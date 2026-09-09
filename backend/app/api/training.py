"""Training API: Vanna RAG training (DDL, documentation, question-SQL pairs)."""
import logging
import os
import tempfile
from pathlib import Path

from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models import TrainingItem
from ..vanna_service import get_vanna_service
from ..bootstrap import get_db_settings, reinitialize_vanna
from ..auth import require_auth, current_user_context

logger = logging.getLogger(__name__)
training_bp = Blueprint("training", __name__, url_prefix="/api/training")

ACCESS_ALL = "all"
ACCESS_AUTHENTICATED = "authenticated"
AUTH_ACCESS_MARKER = "[ACCESS:AUTHENTICATED]"
ALLOWED_KB_EXTENSIONS = {
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".pdf", ".png", ".jpg", ".jpeg"
}


def _normalize_access(raw: str) -> str:
    access = (raw or ACCESS_ALL).strip().lower()
    if access in {"restricted", "logged_in", "logged-in", "auth"}:
        return ACCESS_AUTHENTICATED
    if access not in {ACCESS_ALL, ACCESS_AUTHENTICATED}:
        return ACCESS_ALL
    return access


def _tag_for_vector(text: str, access: str) -> str:
    content = (text or "").strip()
    if access == ACCESS_AUTHENTICATED and not content.startswith(AUTH_ACCESS_MARKER):
        return f"{AUTH_ACCESS_MARKER}\n{content}"
    return content


def _extract_text_from_file(file_path: str, ext: str) -> str:
    ext = (ext or "").lower()
    if ext == ".doc":
        raise RuntimeError("Legacy .doc is not supported directly. Please save as .docx and upload again.")
    if ext == ".xls":
        raise RuntimeError("Legacy .xls is not supported directly. Please save as .xlsx and upload again.")
    if ext == ".ppt":
        raise RuntimeError("Legacy .ppt is not supported directly. Please save as .pptx and upload again.")

    if ext == ".docx":
        try:
            from docx import Document
            doc = Document(file_path)
            blocks = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
            return "\n".join(blocks).strip()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Could not read Word file: {exc}") from exc

    if ext == ".xlsx":
        try:
            from openpyxl import load_workbook
            wb = load_workbook(file_path, data_only=True)
            lines = []
            for sheet in wb.worksheets:
                lines.append(f"Sheet: {sheet.title}")
                for row in sheet.iter_rows(values_only=True):
                    vals = [str(v).strip() for v in row if v is not None and str(v).strip()]
                    if vals:
                        lines.append(" | ".join(vals))
            return "\n".join(lines).strip()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Could not read Excel file: {exc}") from exc

    if ext in {".ppt", ".pptx"}:
        try:
            from pptx import Presentation
            prs = Presentation(file_path)
            lines = []
            for idx, slide in enumerate(prs.slides, start=1):
                lines.append(f"Slide {idx}")
                for shape in slide.shapes:
                    text = getattr(shape, "text", "")
                    if text and text.strip():
                        lines.append(text.strip())
            return "\n".join(lines).strip()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Could not read PowerPoint file: {exc}") from exc

    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            pages = [((p.extract_text() or "").strip()) for p in reader.pages]
            return "\n".join([p for p in pages if p]).strip()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Could not read PDF file: {exc}") from exc

    if ext in {".png", ".jpg", ".jpeg"}:
        try:
            from PIL import Image
            import pytesseract
            return (pytesseract.image_to_string(Image.open(file_path)) or "").strip()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "Could not extract text from image. Install OCR dependencies (pytesseract + Tesseract binary). "
                f"Details: {exc}"
            ) from exc

    raise RuntimeError("Unsupported file type.")


def _ensure_ready():
    svc = get_vanna_service()
    if not svc.ready:
        reinitialize_vanna()
    return svc


@training_bp.route("", methods=["GET"])
@training_bp.route("/", methods=["GET"])
@require_auth
def list_training():
    """List training metadata mirrored in SQLite (plus live Vanna data if available).
    
    Note: Only admins can list training items to prevent cross-tenant data exposure.
    """
    ctx = current_user_context() or {}
    if not ctx.get("is_admin"):
        return jsonify({"success": False, "error": "Admin access required"}), 403
    items = [t.to_dict() for t in TrainingItem.query.order_by(TrainingItem.created_at.desc()).all()]
    live = []
    try:
        live = get_vanna_service().list_training_data()
    except Exception:
        live = []
    return jsonify({"success": True, "items": items, "vanna_data": live}), 200


@training_bp.route("/knowledge-base", methods=["GET"])
@require_auth
def list_knowledge_base():
    ctx = current_user_context() or {}
    if not ctx.get("is_admin"):
        return jsonify({"success": False, "error": "Admin access required"}), 403
    items = [
        t.to_dict()
        for t in TrainingItem.query.filter_by(source_kind="knowledge_base")
        .order_by(TrainingItem.created_at.desc())
        .all()
    ]
    return jsonify({"success": True, "items": items}), 200


@training_bp.route("/knowledge-base/upload", methods=["POST"])
@require_auth
def upload_knowledge_base():
    ctx = current_user_context() or {}
    if not ctx.get("is_admin"):
        return jsonify({"success": False, "error": "Admin access required"}), 403
    svc = _ensure_ready()
    if not svc.ready:
        return jsonify({"success": False, "error": "Engine not ready."}), 503

    incoming = request.files.get("file")
    if incoming is None:
        return jsonify({"success": False, "error": "Missing uploaded file (field name: file)."}), 400

    original_name = secure_filename(incoming.filename or "")
    if not original_name:
        return jsonify({"success": False, "error": "Invalid file name."}), 400

    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_KB_EXTENSIONS:
        return jsonify({"success": False, "error": f"Unsupported file type: {ext}"}), 400

    access = _normalize_access(request.form.get("access"))
    rule = (request.form.get("rule") or "optional").strip().lower()
    if rule not in {"optional", "compulsory"}:
        rule = "optional"

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            incoming.save(tmp.name)
            temp_path = tmp.name

        extracted = _extract_text_from_file(temp_path, ext)
        if not extracted or not extracted.strip():
            return jsonify({"success": False, "error": "No extractable text found in the uploaded file."}), 400

        tagged_text = _tag_for_vector(
            f"Knowledge Base Document: {original_name}\n\n{extracted.strip()}",
            access,
        )
        vid = svc.train_documentation(tagged_text)

        preview = extracted.strip()
        if len(preview) > 8000:
            preview = preview[:8000] + "\n...[truncated preview]"

        item = TrainingItem(
            item_type="documentation",
            rule=rule,
            access=access,
            source_kind="knowledge_base",
            source_name=original_name,
            source_file_type=ext.lstrip("."),
            content=preview,
            vanna_id=str(vid),
        )
        db.session.add(item)
        db.session.commit()
        return jsonify({"success": True, "item": item.to_dict(), "vanna_id": str(vid)}), 200
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return jsonify({"success": False, "error": str(exc)}), 500
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


@training_bp.route("/ddl", methods=["POST"])
@require_auth
def train_ddl():
    ctx = current_user_context() or {}
    if not ctx.get("is_admin"):
        return jsonify({"success": False, "error": "Admin access required"}), 403
    svc = _ensure_ready()
    if not svc.ready:
        return jsonify({"success": False, "error": "Engine not ready."}), 503
    data = request.get_json(silent=True) or {}
    ddl = (data.get("ddl") or "").strip()
    rule = (data.get("rule") or "optional").strip().lower()
    access = _normalize_access(data.get("access"))
    if rule not in {"optional", "compulsory"}:
        rule = "optional"
    if not ddl:
        return jsonify({"success": False, "error": "Missing 'ddl'"}), 400
    try:
        vid = svc.train_ddl(_tag_for_vector(ddl, access))
        db.session.add(TrainingItem(item_type="ddl", rule=rule, access=access, content=ddl, vanna_id=str(vid)))
        db.session.commit()
        return jsonify({"success": True, "vanna_id": str(vid)}), 200
    except Exception as exc:  # noqa: BLE001
        return jsonify({"success": False, "error": str(exc)}), 500


@training_bp.route("/documentation", methods=["POST"])
@require_auth
def train_doc():
    ctx = current_user_context() or {}
    if not ctx.get("is_admin"):
        return jsonify({"success": False, "error": "Admin access required"}), 403
    svc = _ensure_ready()
    if not svc.ready:
        return jsonify({"success": False, "error": "Engine not ready."}), 503
    data = request.get_json(silent=True) or {}
    doc = (data.get("documentation") or "").strip()
    rule = (data.get("rule") or "optional").strip().lower()
    access = _normalize_access(data.get("access"))
    if rule not in {"optional", "compulsory"}:
        rule = "optional"
    if not doc:
        return jsonify({"success": False, "error": "Missing 'documentation'"}), 400
    try:
        vid = svc.train_documentation(_tag_for_vector(doc, access))
        db.session.add(TrainingItem(item_type="documentation", rule=rule, access=access, content=doc, vanna_id=str(vid)))
        db.session.commit()
        return jsonify({"success": True, "vanna_id": str(vid)}), 200
    except Exception as exc:  # noqa: BLE001
        return jsonify({"success": False, "error": str(exc)}), 500


@training_bp.route("/sql", methods=["POST"])
@require_auth
def train_sql():
    ctx = current_user_context() or {}
    if not ctx.get("is_admin"):
        return jsonify({"success": False, "error": "Admin access required"}), 403
    svc = _ensure_ready()
    if not svc.ready:
        return jsonify({"success": False, "error": "Engine not ready."}), 503
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    sql = (data.get("sql") or "").strip()
    rule = (data.get("rule") or "optional").strip().lower()
    access = _normalize_access(data.get("access"))
    if rule not in {"optional", "compulsory"}:
        rule = "optional"
    if not question or not sql:
        return jsonify({"success": False, "error": "Missing 'question' or 'sql'"}), 400
    try:
        vid = svc.train_sql(question, _tag_for_vector(sql, access))
        db.session.add(TrainingItem(item_type="sql", rule=rule, access=access, question=question, content=sql, vanna_id=str(vid)))
        db.session.commit()
        return jsonify({"success": True, "vanna_id": str(vid)}), 200
    except Exception as exc:  # noqa: BLE001
        return jsonify({"success": False, "error": str(exc)}), 500


@training_bp.route("/auto/information-schema", methods=["POST"])
@require_auth
def train_information_schema():
    ctx = current_user_context() or {}
    if not ctx.get("is_admin"):
        return jsonify({"success": False, "error": "Admin access required"}), 403
    svc = _ensure_ready()
    if not svc.ready:
        return jsonify({"success": False, "error": "Engine not ready."}), 503
    db_url = get_db_settings()["source_db_url"]
    if not db_url:
        return jsonify({"success": False, "error": "No source database configured."}), 400
    try:
        result = svc.train_from_information_schema(db_url)
        
        # Create training records for each trained table
        # Store summary in a single documentation item
        trained_count = result.get('items', 0)
        column_count = result.get('columns', 0)
        
        # Create summary record
        db.session.add(TrainingItem(
            item_type="documentation",
            source_kind="auto",
            source_name="information_schema_auto_train",
            content=f"[auto] INFORMATION_SCHEMA: {trained_count} tables, {column_count} columns trained",
            vanna_id=f"auto-info-schema-{int(__import__('time').time())}"
        ))
        db.session.commit()
        
        logger.info(f"✓ Auto-trained on {trained_count} tables from INFORMATION_SCHEMA")
        return jsonify({
            "success": True, 
            "tables_trained": trained_count,
            "columns_trained": column_count,
            "message": f"Auto-trained on {trained_count} tables ({column_count} columns)."
        }), 200
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Auto-train error: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 500


@training_bp.route("/<int:item_id>", methods=["PUT", "PATCH"])
@require_auth
def update_training(item_id):
    """Edit a training item: re-train Vanna with the new content and update the
    SQLite mirror. Body: { content, question? } (question only for sql pairs).
    
    Note: Only admins can update training items.
    """
    ctx = current_user_context() or {}
    if not ctx.get("is_admin"):
        return jsonify({"success": False, "error": "Admin access required"}), 403
    item = TrainingItem.query.get(item_id)
    if not item:
        return jsonify({"success": False, "error": "Not found"}), 404

    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    question = (data.get("question") or "").strip()
    next_type = (data.get("item_type") or item.item_type or "").strip().lower()
    rule = (data.get("rule") or item.rule or "optional").strip().lower()
    access = _normalize_access(data.get("access") or item.access)
    source_kind = (data.get("source_kind") or item.source_kind or "manual").strip().lower()
    source_name = (data.get("source_name") or item.source_name or "").strip() or None
    source_file_type = (data.get("source_file_type") or item.source_file_type or "").strip() or None
    if next_type not in {"ddl", "documentation", "sql"}:
        return jsonify({"success": False, "error": "Invalid 'item_type'"}), 400
    if rule not in {"optional", "compulsory"}:
        rule = "optional"
    if not content:
        return jsonify({"success": False, "error": "Missing 'content'"}), 400
    if next_type == "sql" and not question:
        return jsonify({"success": False, "error": "Missing 'question' for SQL pair"}), 400

    svc = _ensure_ready()
    if not svc.ready:
        return jsonify({"success": False, "error": "Engine not ready."}), 503

    try:
        # Remove the old vector entry, then retrain with the edited content.
        if item.vanna_id:
            svc.remove_training(item.vanna_id)
        if next_type == "ddl":
            vid = svc.train_ddl(_tag_for_vector(content, access))
        elif next_type == "sql":
            vid = svc.train_sql(question, _tag_for_vector(content, access))
        else:
            vid = svc.train_documentation(_tag_for_vector(content, access))

        item.item_type = next_type
        item.rule = rule
        item.access = access
        item.source_kind = source_kind
        item.source_name = source_name
        item.source_file_type = source_file_type
        item.content = content
        item.question = question or None
        item.vanna_id = str(vid)
        db.session.commit()
        return jsonify({"success": True, "item": item.to_dict()}), 200
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return jsonify({"success": False, "error": str(exc)}), 500


@training_bp.route("/<int:item_id>", methods=["DELETE"])
@require_auth
def delete_training(item_id):
    ctx = current_user_context() or {}
    if not ctx.get("is_admin"):
        return jsonify({"success": False, "error": "Admin access required"}), 403
    item = TrainingItem.query.get(item_id)
    if not item:
        return jsonify({"success": False, "error": "Not found"}), 404
    try:
        if item.vanna_id:
            get_vanna_service().remove_training(item.vanna_id)
    except Exception:
        pass
    db.session.delete(item)
    db.session.commit()
    return jsonify({"success": True}), 200


@training_bp.route("/bulk/update", methods=["POST"])
@require_auth
def bulk_update_training():
    """Bulk update training items. Body: { item_ids: [1,2,3], updates: { rule, access, item_type } }
    
    Note: Only admins can bulk update training items.
    """
    ctx = current_user_context() or {}
    if not ctx.get("is_admin"):
        return jsonify({"success": False, "error": "Admin access required"}), 403
    data = request.get_json(silent=True) or {}
    item_ids = data.get("item_ids", [])
    updates = data.get("updates", {})
    
    if not item_ids or not isinstance(item_ids, list):
        return jsonify({"success": False, "error": "Missing or invalid 'item_ids' list"}), 400
    
    if not updates or not isinstance(updates, dict):
        return jsonify({"success": False, "error": "Missing or invalid 'updates' object"}), 400
    
    # Validate update fields
    valid_fields = {"rule", "access", "item_type"}
    invalid_fields = set(updates.keys()) - valid_fields
    if invalid_fields:
        return jsonify({
            "success": False,
            "error": f"Invalid fields to update: {', '.join(invalid_fields)}. Allowed: {', '.join(valid_fields)}"
        }), 400
    
    # Normalize values
    rule = updates.get("rule")
    if rule and rule.lower() not in {"optional", "compulsory"}:
        return jsonify({"success": False, "error": "rule must be 'optional' or 'compulsory'"}), 400
    
    access = updates.get("access")
    if access:
        access = _normalize_access(access)
    
    item_type = updates.get("item_type")
    if item_type and item_type.lower() not in {"ddl", "documentation", "sql"}:
        return jsonify({"success": False, "error": "item_type must be 'ddl', 'documentation', or 'sql'"}), 400
    
    try:
        items = TrainingItem.query.filter(TrainingItem.id.in_(item_ids)).all()
        if not items:
            return jsonify({"success": False, "error": "No items found with the provided IDs"}), 404
        
        for item in items:
            if rule:
                item.rule = rule.lower()
            if access:
                item.access = access
            if item_type:
                item.item_type = item_type.lower()
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "updated_count": len(items),
            "items": [item.to_dict() for item in items]
        }), 200
    
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        logger.error(f"Bulk update failed: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 500
