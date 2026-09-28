"""Train Vanna with table relationships and documentation."""
import logging

from flask import Blueprint, jsonify, request
from ..extensions import db
from ..models import TrainingItem
from ..vanna_service import get_vanna_service
from ..auth import require_auth, current_user_context

logger = logging.getLogger(__name__)
relationships_bp = Blueprint("relationships", __name__, url_prefix="/api/training/relationships")


@relationships_bp.route("/train-schema-docs", methods=["POST"])
@require_auth
def train_schema_documentation():
    """
    Train Vanna with comprehensive table relationships and documentation.
    
    This helps the LLM understand:
    - Which tables have email/contact information
    - How tables relate to each other (foreign keys)
    - What each column represents
    
    Request body:
    {
        "tables_info": [
            {
                "table_name": "contacts",
                "description": "Customer contact information",
                "columns": {
                    "id": "Unique contact ID",
                    "email": "Customer email address",
                    "phone": "Customer phone number",
                    "name": "Full customer name",
                    "company_id": "FK to companies table"
                }
            },
            {
                "table_name": "jobs",
                "description": "Work/project jobs assigned to customers",
                "columns": {
                    "id": "Job number",
                    "customerid": "FK to contacts.id",
                    "description": "Job description",
                    "amount": "Job cost",
                    "status": "Current job status"
                }
            }
        ]
    }
    """
    try:
        ctx = current_user_context() or {}
        if not ctx.get("is_admin"):
            return jsonify({"success": False, "error": "Admin access required"}), 403
        
        data = request.get_json() or {}
        tables_info = data.get("tables_info") or []
        
        if not tables_info:
            return jsonify({"success": False, "error": "tables_info required"}), 400
        
        svc = get_vanna_service()
        if not svc or not svc.ready:
            return jsonify({"success": False, "error": "Vanna service not ready"}), 503
        
        trained_docs = []
        
        for table_info in tables_info:
            table_name = table_info.get("table_name", "").strip()
            description = table_info.get("description", "").strip()
            columns = table_info.get("columns", {})
            
            if not table_name:
                continue
            
            # Build comprehensive documentation
            doc_lines = [f"# Table: {table_name}"]
            
            if description:
                doc_lines.append(f"\n## Description")
                doc_lines.append(description)
            
            if columns:
                doc_lines.append(f"\n## Columns")
                for col_name, col_desc in columns.items():
                    doc_lines.append(f"- **{col_name}**: {col_desc}")
            
            doc_content = "\n".join(doc_lines)
            
            # Train Vanna with this documentation
            try:
                vanna_id = svc._vn.train(documentation=doc_content)
                
                # Store in database
                training_item = TrainingItem(
                    item_type="documentation",
                    source_kind="auto",
                    source_name=f"schema_relationships_{table_name}",
                    content=doc_content,
                    vanna_id=str(vanna_id)
                )
                db.session.add(training_item)
                trained_docs.append({
                    "table": table_name,
                    "vanna_id": str(vanna_id),
                    "columns": len(columns)
                })
                logger.info(f"✓ Trained documentation for table: {table_name}")
            except Exception as e:
                logger.warning(f"Could not train documentation for {table_name}: {e}")
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "trained": trained_docs,
            "message": f"Trained documentation for {len(trained_docs)} tables"
        }), 200
    
    except Exception as e:
        logger.error(f"Error training schema docs: {e}")
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@relationships_bp.route("/quick-setup", methods=["POST"])
@require_auth
def quick_setup_standard_schema():
    """
    Quick setup for common schema: contacts, jobs, payments, invoices.
    
    This trains Vanna with relationship documentation for standard business database.
    """
    try:
        ctx = current_user_context() or {}
        if not ctx.get("is_admin"):
            return jsonify({"success": False, "error": "Admin access required"}), 403
        
        standard_schema = {
            "tables_info": [
                {
                    "table_name": "contacts",
                    "description": "Customer and contact information. Contains all email addresses and phone numbers for communication.",
                    "columns": {
                        "id": "Unique contact/customer ID - use to link to jobs, invoices, payments",
                        "email": "Customer email address - use for sending invoices, receipts, notifications",
                        "phone": "Customer phone number",
                        "name": "Full customer name",
                        "company": "Company name if applicable",
                        "address": "Physical address",
                        "city": "City",
                        "state": "State/Province",
                        "country": "Country"
                    }
                },
                {
                    "table_name": "jobs",
                    "description": "Work/project jobs. Each job belongs to a customer (contact) and generates an invoice.",
                    "columns": {
                        "id": "Unique job number - reference this in invoices",
                        "customerid": "Foreign key to contacts.id - use to join with contacts to get customer email",
                        "description": "What work was done",
                        "amount": "How much the job costs",
                        "status": "Current job status (pending, completed, paid, etc)",
                        "created_date": "When job was created",
                        "completed_date": "When job was completed"
                    }
                },
                {
                    "table_name": "invoices",
                    "description": "Invoice records for jobs. Use customerid to get email from contacts table for sending.",
                    "columns": {
                        "id": "Invoice number",
                        "jobid": "Foreign key to jobs.id - which job this invoice is for",
                        "customerid": "Foreign key to contacts.id - which customer to send invoice to",
                        "amount": "Invoice total amount",
                        "issued_date": "When invoice was issued",
                        "due_date": "Payment due date",
                        "status": "Invoice status (draft, sent, paid, overdue)"
                    }
                },
                {
                    "table_name": "payments",
                    "description": "Payment records. Tracks which invoices have been paid.",
                    "columns": {
                        "id": "Payment ID",
                        "invoiceid": "Foreign key to invoices.id - which invoice was paid",
                        "customerid": "Foreign key to contacts.id - which customer made payment",
                        "amount": "Payment amount",
                        "payment_date": "When payment was received",
                        "payment_method": "How was it paid (bank transfer, cash, check, etc)",
                        "reference": "Payment reference number"
                    }
                }
            ]
        }
        
        # Call the train_schema_documentation endpoint
        svc = get_vanna_service()
        if not svc or not svc.ready:
            return jsonify({"success": False, "error": "Vanna service not ready"}), 503
        
        trained_docs = []
        
        for table_info in standard_schema["tables_info"]:
            table_name = table_info.get("table_name")
            description = table_info.get("description", "")
            columns = table_info.get("columns", {})
            
            # Build documentation
            doc_lines = [f"# Table: {table_name}"]
            if description:
                doc_lines.append(f"\n## Description\n{description}")
            if columns:
                doc_lines.append("\n## Columns")
                for col_name, col_desc in columns.items():
                    doc_lines.append(f"- **{col_name}**: {col_desc}")
            
            doc_content = "\n".join(doc_lines)
            
            # Train Vanna
            try:
                vanna_id = svc._vn.train(documentation=doc_content)
                training_item = TrainingItem(
                    item_type="documentation",
                    source_kind="auto",
                    source_name=f"schema_relationships_{table_name}",
                    content=doc_content,
                    vanna_id=str(vanna_id)
                )
                db.session.add(training_item)
                trained_docs.append(table_name)
                logger.info(f"✓ Quick-setup trained: {table_name}")
            except Exception as e:
                logger.warning(f"Could not train {table_name}: {e}")
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "trained_tables": trained_docs,
            "message": f"✅ Quick setup complete: trained {len(trained_docs)} standard business tables"
        }), 200
    
    except Exception as e:
        logger.error(f"Error in quick setup: {e}")
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
