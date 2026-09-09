"""Data Exchange API: import a brainz export and train Vanna with the same data.

The companion `brainz` app exports configuration from Settings → Data Exchange as
a JSON document with keys like `rag_records`, `business_rules`, `app_settings`,
etc. This endpoint ingests that document and trains the Vanna vector store so
this project's text-to-SQL is grounded in the SAME schema, relationships and
business rules.

Mapping into Vanna training:
  - rag_records.schema_text   -> DDL (if it contains CREATE TABLE) else documentation
  - rag_records.relationships -> documentation
  - rag_records.llm_analysis  -> documentation
  - rag_records.sample_data   -> documentation (trimmed)
  - business_rules            -> documentation ("Business rule: <title>\n<description>")
"""
import json
import logging
from typing import Any, Dict, List
from io import BytesIO
import sqlite3
from datetime import datetime

from flask import Blueprint, request, jsonify, send_file
from sqlalchemy import text, inspect

from ..extensions import db
from ..models import TrainingItem
from ..vanna_service import get_vanna_service
from ..bootstrap import reinitialize_vanna
from ..auth import require_auth, current_user_context
from ..config import Config

logger = logging.getLogger(__name__)
data_exchange_bp = Blueprint("data_exchange", __name__, url_prefix="/api/data-exchange")


@data_exchange_bp.route("/export", methods=["GET"])
@require_auth
def export_training_data():
    """Export local training data in a portable JSON envelope (admin/auth only)."""
    ctx = current_user_context() or {}
    if not ctx.get("is_admin"):
        return jsonify({"success": False, "error": "Admin access required"}), 403
    
    items = TrainingItem.query.order_by(TrainingItem.created_at.desc()).all()
    rag_records = []
    for it in items:
        if it.item_type == "ddl":
            rag_records.append({
                "table_name": "manual_ddl",
                "schema_text": it.content,
                "relationships": [],
                "llm_analysis": "",
                "sample_data": [],
                "source": "assistantai",
            })
        elif it.item_type == "documentation":
            rag_records.append({
                "table_name": "documentation",
                "schema_text": "",
                "relationships": [],
                "llm_analysis": it.content,
                "sample_data": [],
                "source": "assistantai",
            })

    sql_pairs = [
        {
            "question": it.question,
            "sql": it.content,
            "created_at": it.created_at.isoformat() if it.created_at else None,
        }
        for it in items
        if it.item_type == "sql"
    ]

    payload = {
        "metadata": {
            "exported_from": "assistantai",
            "version": "1.0",
            "total_items": len(items),
        },
        "rag_records": rag_records,
        "sql_pairs": sql_pairs,
        "business_rules": [],
    }
    return jsonify(payload), 200


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, default=str, indent=2)
    except Exception:
        return str(value)


def _looks_like_ddl(text: str) -> bool:
    t = (text or "").upper()
    return "CREATE TABLE" in t or "CREATE OR REPLACE" in t


@data_exchange_bp.route("/preview", methods=["POST"])
@require_auth
def preview():
    """Summarize an uploaded export without importing it (authenticated users only)."""
    ctx = current_user_context() or {}
    if not ctx.get("is_admin"):
        return jsonify({"success": False, "error": "Admin access required"}), 403
    
    payload = request.get_json(silent=True) or {}
    data = payload.get("export_data", payload)
    return jsonify({
        "success": True,
        "summary": {
            "rag_records": len(data.get("rag_records", []) or []),
            "business_rules": len(data.get("business_rules", []) or []),
            "app_settings": len(data.get("app_settings", []) or []),
            "llm_configs": len(data.get("llm_configs", []) or []),
            "metadata": data.get("metadata", {}),
        },
    }), 200


@data_exchange_bp.route("/import", methods=["POST"])
@require_auth
def import_export():
    """Import a brainz export JSON and train Vanna with it (authenticated users only).

    Body: the export object directly, or { "export_data": {...},
           "include_sample_data": bool }.
    """
    ctx = current_user_context() or {}
    if not ctx.get("is_admin"):
        return jsonify({"success": False, "error": "Admin access required"}), 403
    
    payload = request.get_json(silent=True) or {}
    data = payload.get("export_data", payload)
    include_samples = bool(payload.get("include_sample_data", True))

    if not isinstance(data, dict) or not (data.get("rag_records") or data.get("business_rules")):
        return jsonify({
            "success": False,
            "error": "Invalid export. Expected JSON with 'rag_records' and/or 'business_rules'.",
        }), 400

    svc = get_vanna_service()
    if not svc.ready:
        logger.info("Reinitializing Vanna service...")
        reinitialize_vanna()
    if not svc.ready:
        error_msg = "Text-to-SQL engine not ready. Configure LLM + Vector DB first."
        logger.error(f"❌ Import failed: {error_msg}")
        return jsonify({"success": False, "error": error_msg}), 503

    counts = {"ddl": 0, "documentation": 0, "sql": 0, "skipped": 0, "errors": 0}
    errors_list = []

    def _train(item_type: str, content: str, question: str = "") -> None:
        content = (content or "").strip()
        if not content:
            counts["skipped"] += 1
            return
        try:
            if item_type == "ddl":
                vid = svc.train_ddl(content)
            elif item_type == "sql":
                vid = svc.train_sql(question, content)
            else:
                vid = svc.train_documentation(content)
            db.session.add(TrainingItem(
                item_type=item_type, question=question or None, content=content, vanna_id=str(vid),
            ))
            counts[item_type] += 1
        except Exception as exc:  # noqa: BLE001
            error_detail = f"Training failed for {item_type}: {type(exc).__name__}: {str(exc)[:200]}"
            logger.error(f"❌ {error_detail}")
            errors_list.append(error_detail)
            counts["errors"] += 1

    # ----- RAG records (schema + relationships + analysis + samples) ----- #
    for rec in (data.get("rag_records") or []):
        if not isinstance(rec, dict):
            continue
        table = rec.get("table_name") or "table"
        schema_text = _as_text(rec.get("schema_text"))
        if schema_text:
            if _looks_like_ddl(schema_text):
                _train("ddl", schema_text)
            else:
                _train("documentation", f"Schema for table '{table}':\n{schema_text}")

        relationships = _as_text(rec.get("relationships"))
        if relationships and relationships not in ("[]", "{}", "null"):
            _train("documentation", f"Relationships for table '{table}':\n{relationships}")

        analysis = _as_text(rec.get("llm_analysis"))
        if analysis and analysis not in ("[]", "{}", "null"):
            _train("documentation", f"Notes about table '{table}':\n{analysis}")

        if include_samples:
            samples = _as_text(rec.get("sample_data"))
            if samples and samples not in ("[]", "{}", "null"):
                _train("documentation", f"Sample rows from table '{table}':\n{samples[:4000]}")

    # ----- Business rules ----- #
    for rule in (data.get("business_rules") or []):
        if not isinstance(rule, dict):
            continue
        title = rule.get("title") or "Business rule"
        desc = _as_text(rule.get("description"))
        category = rule.get("category") or ""
        text = f"Business rule [{category}] — {title}\n{desc}".strip()
        _train("documentation", text)

    db.session.commit()

    total = counts["ddl"] + counts["documentation"] + counts["sql"]
    
    if counts["errors"] > 0:
        logger.error(f"❌ Import completed with {counts['errors']} errors: {counts}")
        first_error = errors_list[0] if errors_list else "Unknown error"
        return jsonify({
            "success": total > 0,
            "message": f"Imported {total} item(s), but {counts['errors']} failed to train. Check server logs for details.",
            "counts": counts,
            "first_error": first_error,
            "note": "Use Settings → Server Logs to view detailed error messages"
        }), 200 if total > 0 else 400
    
    logger.info(f"✅ Data Exchange import complete: {counts}")
    return jsonify({
        "success": True,
        "message": f"Successfully imported and trained {total} item(s) into Vanna.",
        "counts": counts,
    }), 200


# ============================= Database Export/Import ============================= #

@data_exchange_bp.route("/database/export", methods=["POST"])
@require_auth
def export_database():
    """Export entire SQLite admin database as JSON (admin-only).
    
    Returns a JSON file containing all tables, schema, and data from the admin database.
    Can be imported into another instance of assistantai.
    
    Request body (optional):
    {
        "format": "json|sql",  // json (default) or sql dump format
        "exclude_tables": ["table1", "table2"],  // Optional: tables to exclude
        "pretty": true  // Optional: pretty-print JSON (default: false for smaller size)
    }
    """
    ctx = current_user_context() or {}
    if not ctx.get("is_admin"):
        return jsonify({"success": False, "error": "Admin access required"}), 403
    
    data = request.get_json(silent=True) or {}
    export_format = data.get("format", "json").lower()
    exclude_tables = set(data.get("exclude_tables", []))
    pretty = bool(data.get("pretty", False))
    
    if export_format not in ("json", "sql"):
        return jsonify({"success": False, "error": "Format must be 'json' or 'sql'"}), 400
    
    try:
        # Get inspector for current database
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        # Filter out system tables and excluded tables
        tables = [t for t in tables if not t.startswith('sqlite_') and t not in exclude_tables]
        
        if export_format == "sql":
            # SQL dump format
            sql_dump = _export_as_sql_dump(tables)
            filename = f"assistantai_db_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
            
            # Return as downloadable file
            return send_file(
                BytesIO(sql_dump.encode('utf-8')),
                mimetype='text/plain',
                as_attachment=True,
                download_name=filename
            )
        else:
            # JSON format (default)
            export_data = _export_as_json(tables)
            
            return jsonify({
                "success": True,
                "data": export_data,
                "metadata": {
                    "exported_at": datetime.now().isoformat(),
                    "tables_exported": len(tables),
                    "format": "json",
                    "app_version": "1.0",
                }
            }), 200
            
    except Exception as e:
        logger.error(f"Database export error: {e}")
        return jsonify({"success": False, "error": f"Export failed: {str(e)}"}), 500


def _export_as_json(table_names: List[str]) -> Dict[str, Any]:
    """Export database tables as JSON structure."""
    export_data = {
        "metadata": {
            "exported_at": datetime.now().isoformat(),
            "format_version": "1.0",
            "app": "assistantai",
        },
        "tables": {}
    }
    
    for table_name in table_names:
        try:
            # Get table schema
            inspector = inspect(db.engine)
            columns = inspector.get_columns(table_name)
            primary_keys = inspector.get_pk_constraint(table_name)
            
            # Get table data
            result = db.session.execute(text(f'SELECT * FROM "{table_name}"'))
            rows = result.fetchall()
            
            table_data = {
                "schema": {
                    "columns": [
                        {
                            "name": c["name"],
                            "type": str(c["type"]),
                            "nullable": c.get("nullable", True),
                            "default": str(c.get("default")) if c.get("default") else None,
                        }
                        for c in columns
                    ],
                    "primary_keys": primary_keys.get("constrained_columns", []) if primary_keys else [],
                },
                "data": []
            }
            
            # Convert rows to dictionaries
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    val = row[i]
                    # Handle special types for JSON serialization
                    if isinstance(val, bytes):
                        row_dict[col["name"]] = f"<binary:{len(val)} bytes>"
                    elif val is None:
                        row_dict[col["name"]] = None
                    else:
                        row_dict[col["name"]] = val
                table_data["data"].append(row_dict)
            
            export_data["tables"][table_name] = table_data
            logger.debug(f"✓ Exported table '{table_name}' ({len(rows)} rows)")
            
        except Exception as e:
            logger.warning(f"Could not export table '{table_name}': {e}")
            export_data["tables"][table_name] = {"schema": {}, "data": [], "error": str(e)}
    
    return export_data


def _export_as_sql_dump(table_names: List[str]) -> str:
    """Export database tables as SQL statements."""
    sql_lines = [
        "-- SQLite Database Export",
        f"-- Exported: {datetime.now().isoformat()}",
        f"-- Tables: {', '.join(table_names)}",
        "",
        "PRAGMA foreign_keys = OFF;",
        ""
    ]
    
    for table_name in table_names:
        try:
            # Get CREATE TABLE statement
            cursor = db.engine.raw_connection().cursor()
            cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            result = cursor.fetchone()
            
            if result:
                create_stmt = result[0]
                sql_lines.append(f"-- Table: {table_name}")
                sql_lines.append(f"DROP TABLE IF EXISTS {table_name};")
                sql_lines.append(create_stmt + ";")
                sql_lines.append("")
                
                # Get data
                data_cursor = db.engine.raw_connection().cursor()
                data_cursor.execute(f'SELECT * FROM "{table_name}"')
                rows = data_cursor.fetchall()
                
                # Get column names
                col_cursor = db.engine.raw_connection().cursor()
                col_cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [row[1] for row in col_cursor.fetchall()]
                
                if rows:
                    col_names = ', '.join([f'"{c}"' for c in columns])
                    for row in rows:
                        values = []
                        for val in row:
                            if val is None:
                                values.append("NULL")
                            elif isinstance(val, str):
                                escaped = val.replace("'", "''")
                                values.append(f"'{escaped}'")
                            elif isinstance(val, (int, float)):
                                values.append(str(val))
                            else:
                                values.append(f"'{str(val)}'")
                        
                        insert_stmt = f"INSERT INTO {table_name} ({col_names}) VALUES ({', '.join(values)});"
                        sql_lines.append(insert_stmt)
                    
                    sql_lines.append("")
                    logger.debug(f"✓ Exported {len(rows)} rows from '{table_name}'")
                
        except Exception as e:
            sql_lines.append(f"-- Error exporting table '{table_name}': {e}")
            logger.warning(f"Could not export table '{table_name}': {e}")
    
    sql_lines.extend([
        "PRAGMA foreign_keys = ON;",
        "-- End of export"
    ])
    
    return "\n".join(sql_lines)


@data_exchange_bp.route("/database/import", methods=["POST"])
@require_auth
def import_database():
    """Import entire SQLite database from exported JSON (admin-only).
    
    Merges imported data with existing database. Existing records are NOT deleted.
    Use strategy parameter to control behavior for duplicate keys.
    
    Request body:
    {
        "export_data": { ...exported JSON... },
        "strategy": "merge|replace|skip",  // merge: keep both (default), replace: overwrite, skip: keep existing
        "tables": ["table1", "table2"],  // Optional: only import these tables
    }
    """
    ctx = current_user_context() or {}
    if not ctx.get("is_admin"):
        return jsonify({"success": False, "error": "Admin access required"}), 403
    
    payload = request.get_json(silent=True) or {}
    export_data = payload.get("export_data")
    strategy = payload.get("strategy", "merge").lower()
    import_tables = set(payload.get("tables", []))
    
    if not export_data or not isinstance(export_data, dict):
        return jsonify({"success": False, "error": "Missing or invalid 'export_data' in request"}), 400
    
    if strategy not in ("merge", "replace", "skip"):
        return jsonify({"success": False, "error": "Strategy must be 'merge', 'replace', or 'skip'"}), 400
    
    tables = export_data.get("tables", {})
    if not isinstance(tables, dict):
        return jsonify({"success": False, "error": "Invalid export format: 'tables' must be a dictionary"}), 400
    
    try:
        import_stats = {
            "tables_processed": 0,
            "rows_imported": 0,
            "rows_skipped": 0,
            "errors": 0,
        }
        
        for table_name, table_data in tables.items():
            # Skip if not in selected tables list (if specified)
            if import_tables and table_name not in import_tables:
                continue
            
            # Skip system tables
            if table_name.startswith('sqlite_'):
                continue
            
            try:
                schema = table_data.get("schema", {})
                rows = table_data.get("data", [])
                
                if not schema or not rows:
                    logger.debug(f"Skipping table '{table_name}': no schema or data")
                    continue
                
                # Check if table exists
                inspector = inspect(db.engine)
                table_exists = table_name in inspector.get_table_names()
                
                if not table_exists:
                    logger.warning(f"Table '{table_name}' does not exist in target database. Skipping.")
                    import_stats["errors"] += 1
                    continue
                
                # Import rows based on strategy
                for row in rows:
                    try:
                        if strategy == "replace":
                            # Delete existing record if it has a primary key match
                            pk_cols = schema.get("primary_keys", [])
                            if pk_cols:
                                where_parts = [f'"{col}" = :{col}' for col in pk_cols]
                                where_clause = " AND ".join(where_parts)
                                db.session.execute(text(f'DELETE FROM "{table_name}" WHERE {where_clause}'), row)
                        
                        elif strategy == "skip":
                            # Check if record exists
                            pk_cols = schema.get("primary_keys", [])
                            if pk_cols:
                                where_parts = [f'"{col}" = :{col}' for col in pk_cols]
                                where_clause = " AND ".join(where_parts)
                                result = db.session.execute(
                                    text(f'SELECT COUNT(*) FROM "{table_name}" WHERE {where_clause}'),
                                    row
                                )
                                if result.scalar() > 0:
                                    import_stats["rows_skipped"] += 1
                                    continue
                        
                        # Insert row
                        cols = list(row.keys())
                        col_names = ', '.join([f'"{c}"' for c in cols])
                        placeholders = ', '.join([f':{c}' for c in cols])
                        insert_sql = f'INSERT OR IGNORE INTO "{table_name}" ({col_names}) VALUES ({placeholders})'
                        
                        db.session.execute(text(insert_sql), row)
                        import_stats["rows_imported"] += 1
                        
                    except Exception as row_error:
                        logger.warning(f"Error importing row from '{table_name}': {row_error}")
                        import_stats["errors"] += 1
                        continue
                
                import_stats["tables_processed"] += 1
                logger.info(f"✓ Imported {len(rows)} rows into '{table_name}' (strategy: {strategy})")
                
            except Exception as table_error:
                logger.error(f"Error processing table '{table_name}': {table_error}")
                import_stats["errors"] += 1
                continue
        
        db.session.commit()
        
        logger.info(f"✅ Database import complete: {import_stats}")
        return jsonify({
            "success": True,
            "message": f"Imported {import_stats['tables_processed']} table(s), {import_stats['rows_imported']} row(s)",
            "stats": import_stats,
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Database import error: {e}")
        return jsonify({"success": False, "error": f"Import failed: {str(e)}"}), 500
