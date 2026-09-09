"""Swagger / OpenAPI documentation for the assistantai backend.

Uses flasgger to serve an interactive Swagger UI built from a curated spec
(no per-route docstrings required). The spec is grouped by tags and documents
every public endpoint, including the three authentication strategies and the
mandatory company-level data isolation applied to query endpoints.

Mounting:
    - Swagger UI:   GET /api/docs/
    - Raw spec:     GET /api/openapi.json
"""
from flasgger import Swagger

API_VERSION = "1.0.0"

# --------------------------------------------------------------------------- #
# Reusable building blocks
# --------------------------------------------------------------------------- #
_BEARER = [{"Bearer": []}]

_SECURITY_DEFINITIONS = {
    "Bearer": {
        "type": "apiKey",
        "name": "Authorization",
        "in": "header",
        "description": (
            "JWT bearer token. Send as: `Authorization: Bearer <token>`.\n\n"
            "Obtain a token via `/api/auth/login` (internal users), "
            "`/api/auth/token-login` (external JWT exchange), or use a "
            "microservice-issued token directly when `MICROSERVICE_MODE=true`."
        ),
    }
}

_TAGS = [
    {"name": "Health", "description": "Service health and engine status."},
    {"name": "Authentication", "description": "Login, registration, token exchange, and identity."},
    {"name": "Chat & Query", "description": "Natural-language to SQL querying with multi-turn context."},
    {"name": "Conversations", "description": "Manage saved multi-turn conversations."},
    {"name": "Training", "description": "Vanna RAG training data (DDL, documentation, Q/SQL) and knowledge base."},
    {"name": "Settings", "description": "LLM, database, vector store, and engine configuration."},
    {"name": "Access Control", "description": "Table-level role access mappings."},
    {"name": "Auth Config", "description": "SOURCE database authentication table/field mappings."},
    {"name": "Security", "description": "Restricted SQL commands and banned keywords."},
    {"name": "Cache & Audit", "description": "Query metrics, recent queries, and audit logs."},
    {"name": "Data Exchange", "description": "Import/export of training and configuration data."},
]


def _ok(description="Successful response"):
    return {"description": description}


def _err(description):
    return {"description": description}


def _json_body(name, properties, required=None, description=""):
    """Build a Swagger 2.0 body parameter."""
    schema = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return {
        "name": name,
        "in": "body",
        "required": True,
        "description": description,
        "schema": schema,
    }


def _str(example=None, description=""):
    p = {"type": "string"}
    if example is not None:
        p["example"] = example
    if description:
        p["description"] = description
    return p


def _int(example=None, description=""):
    p = {"type": "integer"}
    if example is not None:
        p["example"] = example
    if description:
        p["description"] = description
    return p


def _bool(example=None, description=""):
    p = {"type": "boolean"}
    if example is not None:
        p["example"] = example
    if description:
        p["description"] = description
    return p


def _path_param(name, description="", ptype="string"):
    return {"name": name, "in": "path", "required": True, "type": ptype, "description": description}


def _query_param(name, description="", ptype="string", required=False):
    return {"name": name, "in": "query", "required": required, "type": ptype, "description": description}


# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
def _build_paths():
    return {
        # ---------------- Health ---------------- #
        "/api/health": {
            "get": {
                "tags": ["Health"],
                "summary": "Health check + text-to-SQL engine status",
                "responses": {"200": _ok("Service is up; includes engine status.")},
            }
        },
        "/api/settings/engine/status": {
            "get": {
                "tags": ["Health"],
                "summary": "Get text-to-SQL engine status",
                "responses": {"200": _ok()},
            }
        },
        "/api/settings/engine/reinitialize": {
            "post": {
                "tags": ["Health"],
                "summary": "Reinitialize the text-to-SQL engine",
                "security": _BEARER,
                "responses": {"200": _ok()},
            }
        },

        # ---------------- Authentication ---------------- #
        "/api/auth/login": {
            "post": {
                "tags": ["Authentication"],
                "summary": "Login with username/email + password",
                "parameters": [_json_body("credentials", {
                    "username": _str("admin", "Username or email"),
                    "email": _str("user@example.com", "Alternative to username (do not hardcode)"),
                    "password": _str("secret"),
                }, required=["password"])],
                "responses": {
                    "200": _ok("Returns JWT token and user profile."),
                    "401": _err("Invalid credentials."),
                },
            }
        },
        "/api/auth/register": {
            "post": {
                "tags": ["Authentication"],
                "summary": "Register a new internal user",
                "parameters": [_json_body("user", {
                    "username": _str("jdoe"),
                    "email": _str("jdoe@example.com"),
                    "password": _str("secret"),
                    "first_name": _str("John"),
                    "last_name": _str("Doe"),
                    "company_name": _str("Acme", "Optional; creates/links a company"),
                }, required=["username", "email", "password"])],
                "responses": {"200": _ok(), "409": _err("User already exists.")},
            }
        },
        "/api/auth/token-login": {
            "post": {
                "tags": ["Authentication"],
                "summary": "Exchange an external JWT for an internal token",
                "description": (
                    "Decodes an upstream JWT, resolves the tenant by matching the "
                    "`parentCompanyCode` claim to the SOURCE `company.company_code`, "
                    "and returns an internal token whose `company_fk` is the SOURCE "
                    "company id (plus child-branch ids for data isolation)."
                ),
                "parameters": [_json_body("payload", {
                    "token": _str("eyJhbGciOiJSUzI1NiJ9...", "External JWT with parentCompanyCode claim"),
                }, required=["token"])],
                "responses": {
                    "200": _ok("Returns internal token and resolved user/company."),
                    "401": _err("Invalid token format or missing claims."),
                    "404": _err("Company not found for parentCompanyCode."),
                },
            }
        },
        "/api/auth/me": {
            "get": {
                "tags": ["Authentication"],
                "summary": "Get the current authenticated user's profile",
                "security": _BEARER,
                "responses": {"200": _ok(), "401": _err("Authentication required.")},
            }
        },
        "/api/auth/verify-email": {
            "post": {
                "tags": ["Authentication"],
                "summary": "Verify an email exists in the SOURCE user table",
                "parameters": [_json_body("payload", {"email": _str("user@example.com")}, required=["email"])],
                "responses": {"200": _ok()},
            }
        },
        "/api/auth/companies-by-email": {
            "post": {
                "tags": ["Authentication"],
                "summary": "List companies associated with an email",
                "parameters": [_json_body("payload", {"email": _str("user@example.com")}, required=["email"])],
                "responses": {"200": _ok()},
            }
        },
        "/api/auth/source-db-login": {
            "post": {
                "tags": ["Authentication"],
                "summary": "Authenticate against the configured SOURCE database",
                "parameters": [_json_body("credentials", {
                    "email": _str("user@example.com"),
                    "password": _str("secret"),
                }, required=["email", "password"])],
                "responses": {"200": _ok(), "401": _err("Invalid credentials.")},
            }
        },
        "/api/auth/finalize-source-login": {
            "post": {
                "tags": ["Authentication"],
                "summary": "Finalize SOURCE login by selecting a company",
                "parameters": [_json_body("payload", {
                    "email": _str("user@example.com"),
                    "company_id": _int(528),
                }, required=["email", "company_id"])],
                "responses": {"200": _ok()},
            }
        },

        # ---------------- Chat & Query ---------------- #
        "/api/chat/query": {
            "post": {
                "tags": ["Chat & Query"],
                "summary": "Natural-language query → SQL → answer (multi-turn conversation support)",
                "description": (
                    "Routes intent (database / knowledge-base / direct), generates SQL "
                    "via RAG with multi-turn context, enforces SELECT-only safety and "
                    "MANDATORY company_fk data isolation, executes with a self-correction "
                    "loop, then returns a conversational answer plus analysis.\n\n"
                    "**Multi-turn conversations:** To continue a previous conversation, pass the "
                    "`conversation_id` from the initial response. The API will consolidate your new "
                    "question with full history context before generating SQL. Omit `conversation_id` "
                    "to start a fresh conversation."
                ),
                "security": _BEARER,
                "parameters": [_json_body("payload", {
                    "query": _str("How many complaints did we receive in January?", "Required: natural language question/command"),
                    "message": _str(None, "Optional: alias for 'query' (use either one)"),
                    "conversation_id": _str("conv_a1b2c3d4e5f6", 
                        "Optional: ID of conversation to continue. If omitted, a new conversation is created. "
                        "Get the ID from the first response and pass it in subsequent messages."),
                    "is_first_message": _bool(False, 
                        "Optional: override to force marking this message as first in conversation (advanced use only)"),
                }, required=["query"])],
                "responses": {
                    "200": _ok("Answer, generated SQL, rows, analysis, and conversation_id for follow-ups."),
                    "401": _err("Authentication required."),
                    "403": _err("Guest users blocked / table access denied."),
                    "503": _err("Engine not ready."),
                },
            }
        },
        "/api/chat/query/guest": {
            "post": {
                "tags": ["Chat & Query"],
                "summary": "Guest-scoped natural-language query",
                "security": _BEARER,
                "parameters": [_json_body("payload", {
                    "query": _str("Show published help articles"),
                    "conversation_id": _str("conv_guest_1"),
                }, required=["query"])],
                "responses": {"200": _ok(), "403": _err("Only the guest user may use this route.")},
            }
        },
        "/api/chat/public": {
            "post": {
                "tags": ["Chat & Query"],
                "summary": "Public docs assistant (no login required)",
                "description": (
                    "Unauthenticated assistant for users who are NOT logged in. Answers "
                    "**only** from training documentation marked available to non-logged-in "
                    "users (`access=all`) via RAG retrieval. **Never generates or runs SQL** "
                    "and never touches the SOURCE database — it returns an articulated answer "
                    "composed from public documentation."
                ),
                "parameters": [_json_body("payload", {
                    "query": _str("How do I reset my password?"),
                    "message": _str(None, "Alias for 'query'"),
                }, required=["query"])],
                "responses": {
                    "200": _ok("Articulated answer from public docs (mode=knowledge_base, sql_query=null)."),
                    "400": _err("Missing query or restricted keyword."),
                    "503": _err("Knowledge base not ready."),
                },
            }
        },
        "/api/chat/run-sql": {
            "post": {
                "tags": ["Chat & Query"],
                "summary": "Execute a (possibly edited) SELECT statement",
                "description": "Re-applies SELECT-only validation and company_fk enforcement before running.",
                "security": _BEARER,
                "parameters": [_json_body("payload", {
                    "sql": _str("SELECT COUNT(*) FROM complaint"),
                }, required=["sql"])],
                "responses": {"200": _ok(), "400": _err("Blocked unsafe SQL."), "503": _err("No source DB connected.")},
            }
        },
        "/api/chat/refresh": {
            "post": {
                "tags": ["Chat & Query"],
                "summary": "Re-run a previously generated SQL query",
                "security": _BEARER,
                "parameters": [_json_body("payload", {
                    "sql_query": _str("SELECT COUNT(*) FROM complaint WHERE company_fk = 528"),
                }, required=["sql_query"])],
                "responses": {"200": _ok(), "400": _err("Blocked unsafe SQL.")},
            }
        },

        # ---------------- Conversations ---------------- #
        "/api/conversations": {
            "get": {
                "tags": ["Conversations"],
                "summary": "List the current user's conversations",
                "security": _BEARER,
                "responses": {"200": _ok()},
            }
        },
        "/api/conversations/{conversation_id}": {
            "get": {
                "tags": ["Conversations"],
                "summary": "Get a single conversation with messages",
                "security": _BEARER,
                "parameters": [_path_param("conversation_id")],
                "responses": {"200": _ok(), "403": _err("Access denied."), "404": _err("Not found.")},
            },
            "delete": {
                "tags": ["Conversations"],
                "summary": "Delete a conversation",
                "security": _BEARER,
                "parameters": [_path_param("conversation_id")],
                "responses": {"200": _ok(), "403": _err("Access denied."), "404": _err("Not found.")},
            },
        },
        "/api/conversations/{conversation_id}/rename": {
            "post": {
                "tags": ["Conversations"],
                "summary": "Rename a conversation",
                "security": _BEARER,
                "parameters": [
                    _path_param("conversation_id"),
                    _json_body("payload", {"title": _str("Q1 complaints analysis")}, required=["title"]),
                ],
                "responses": {"200": _ok(), "404": _err("Not found.")},
            }
        },
        "/api/conversations/{conversation_id}/messages": {
            "patch": {
                "tags": ["Conversations"],
                "summary": "Update (append/replace) conversation messages",
                "security": _BEARER,
                "parameters": [
                    _path_param("conversation_id"),
                    _json_body("payload", {"messages": {"type": "array", "items": {"type": "object"}}}),
                ],
                "responses": {"200": _ok(), "404": _err("Not found.")},
            }
        },

        # ---------------- Training ---------------- #
        "/api/training": {
            "get": {
                "tags": ["Training"],
                "summary": "List training items",
                "security": _BEARER,
                "parameters": [_query_param("item_type", "Filter: ddl | documentation | sql")],
                "responses": {"200": _ok()},
            }
        },
        "/api/training/ddl": {
            "post": {
                "tags": ["Training"],
                "summary": "Train a DDL statement",
                "security": _BEARER,
                "parameters": [_json_body("payload", {"content": _str("CREATE TABLE complaint (...)")}, required=["content"])],
                "responses": {"200": _ok()},
            }
        },
        "/api/training/documentation": {
            "post": {
                "tags": ["Training"],
                "summary": "Train a documentation snippet",
                "security": _BEARER,
                "parameters": [_json_body("payload", {"content": _str("The complaint table stores customer feedback.")}, required=["content"])],
                "responses": {"200": _ok()},
            }
        },
        "/api/training/sql": {
            "post": {
                "tags": ["Training"],
                "summary": "Train a question → SQL pair",
                "security": _BEARER,
                "parameters": [_json_body("payload", {
                    "question": _str("How many complaints this month?"),
                    "content": _str("SELECT COUNT(*) FROM complaint WHERE ..."),
                }, required=["question", "content"])],
                "responses": {"200": _ok()},
            }
        },
        "/api/training/auto/information-schema": {
            "post": {
                "tags": ["Training"],
                "summary": "Auto-train on the SOURCE INFORMATION_SCHEMA",
                "security": _BEARER,
                "responses": {"200": _ok()},
            }
        },
        "/api/training/knowledge-base": {
            "get": {
                "tags": ["Training"],
                "summary": "List knowledge-base documents",
                "security": _BEARER,
                "responses": {"200": _ok()},
            }
        },
        "/api/training/knowledge-base/upload": {
            "post": {
                "tags": ["Training"],
                "summary": "Upload a knowledge-base file (pdf/docx/xlsx/pptx/image)",
                "security": _BEARER,
                "consumes": ["multipart/form-data"],
                "parameters": [{
                    "name": "file", "in": "formData", "required": True, "type": "file",
                    "description": "Document to ingest into the knowledge base.",
                }],
                "responses": {"200": _ok()},
            }
        },
        "/api/training/{item_id}": {
            "put": {
                "tags": ["Training"],
                "summary": "Update a training item",
                "security": _BEARER,
                "parameters": [_path_param("item_id", ptype="integer"),
                               _json_body("payload", {"content": _str("...")})],
                "responses": {"200": _ok(), "404": _err("Not found.")},
            },
            "delete": {
                "tags": ["Training"],
                "summary": "Delete a training item",
                "security": _BEARER,
                "parameters": [_path_param("item_id", ptype="integer")],
                "responses": {"200": _ok(), "404": _err("Not found.")},
            },
        },
        "/api/training/bulk/update": {
            "post": {
                "tags": ["Training"],
                "summary": "Bulk update training items (rule/access)",
                "security": _BEARER,
                "parameters": [_json_body("payload", {
                    "ids": {"type": "array", "items": {"type": "integer"}},
                    "rule": _str("compulsory"),
                    "access": _str("authenticated"),
                })],
                "responses": {"200": _ok()},
            }
        },

        # ---------------- Settings ---------------- #
        "/api/settings/llm": {
            "get": {"tags": ["Settings"], "summary": "Get LLM settings", "security": _BEARER, "responses": {"200": _ok()}},
            "post": {
                "tags": ["Settings"], "summary": "Update LLM settings", "security": _BEARER,
                "parameters": [_json_body("payload", {
                    "provider": _str("gemini"), "model": _str("gemini-2.5-flash"),
                    "gemini_api_key": _str("•••• (write-only)"),
                })],
                "responses": {"200": _ok()},
            },
        },
        "/api/settings/llm/providers": {
            "get": {"tags": ["Settings"], "summary": "List available LLM providers", "responses": {"200": _ok()}}
        },
        "/api/settings/database": {
            "get": {"tags": ["Settings"], "summary": "Get SOURCE database settings", "security": _BEARER, "responses": {"200": _ok()}},
            "post": {
                "tags": ["Settings"], "summary": "Update SOURCE database settings", "security": _BEARER,
                "parameters": [_json_body("payload", {"source_db_url": _str("postgresql+psycopg2://user:pass@host:5432/db")})],
                "responses": {"200": _ok()},
            },
        },
        "/api/settings/database/test": {
            "post": {
                "tags": ["Settings"], "summary": "Test a SOURCE database connection", "security": _BEARER,
                "parameters": [_json_body("payload", {"source_db_url": _str("postgresql+psycopg2://...")})],
                "responses": {"200": _ok(), "400": _err("Connection failed.")},
            }
        },
        "/api/settings/database/info": {
            "get": {"tags": ["Settings"], "summary": "Get SOURCE database info", "security": _BEARER, "responses": {"200": _ok()}}
        },
        "/api/settings/vector": {
            "get": {"tags": ["Settings"], "summary": "Get vector store settings", "security": _BEARER, "responses": {"200": _ok()}},
            "post": {"tags": ["Settings"], "summary": "Update vector store settings", "security": _BEARER,
                     "parameters": [_json_body("payload", {"vector_store": _str("chromadb")})], "responses": {"200": _ok()}},
        },
        "/api/settings/vector/stores": {
            "get": {"tags": ["Settings"], "summary": "List supported vector stores", "responses": {"200": _ok()}}
        },
        "/api/settings/user": {
            "get": {"tags": ["Settings"], "summary": "Get per-user settings (audio/auto-speak)", "security": _BEARER, "responses": {"200": _ok()}},
            "post": {"tags": ["Settings"], "summary": "Update per-user settings", "security": _BEARER,
                     "parameters": [_json_body("payload", {
                         "audio_settings": {"type": "object"}, "auto_speak": _bool(False)})],
                     "responses": {"200": _ok()}},
        },
        "/api/settings/microservice/status": {
            "get": {"tags": ["Settings"], "summary": "Get microservice-mode status", "responses": {"200": _ok()}}
        },
        "/api/settings/microservice/verify-token": {
            "post": {"tags": ["Settings"], "summary": "Verify a microservice JWT", "security": _BEARER,
                     "parameters": [_json_body("payload", {"token": _str("eyJ...")}, required=["token"])],
                     "responses": {"200": _ok()}},
        },
        "/api/settings/microservice/decode-token": {
            "post": {"tags": ["Settings"], "summary": "Decode (without verifying) a JWT", "security": _BEARER,
                     "parameters": [_json_body("payload", {"token": _str("eyJ...")}, required=["token"])],
                     "responses": {"200": _ok()}},
        },
        "/api/settings/admin-db/info": {
            "get": {"tags": ["Settings"], "summary": "Get admin (local) database info", "security": _BEARER, "responses": {"200": _ok()}}
        },
        "/api/settings/api-doc": {
            "get": {"tags": ["Settings"], "summary": "Get the markdown API developer guide", "responses": {"200": _ok()}}
        },
        "/api/settings/docs": {
            "get": {"tags": ["Settings"], "summary": "List in-app markdown docs", "responses": {"200": _ok()}}
        },
        "/api/settings/docs/{slug}": {
            "get": {"tags": ["Settings"], "summary": "Get a markdown doc by slug", "security": [],
                    "parameters": [_path_param("slug")], "responses": {"200": _ok(), "404": _err("Doc not found.")}}
        },

        # ---------------- Access Control ---------------- #
        "/api/auth-config/table-role-access/tables": {
            "get": {"tags": ["Access Control"], "summary": "List SOURCE tables with role access", "security": _BEARER, "responses": {"200": _ok()}}
        },
        "/api/auth-config/table-role-access/roles": {
            "get": {"tags": ["Access Control"], "summary": "List roles for access mapping", "security": _BEARER, "responses": {"200": _ok()}}
        },
        "/api/auth-config/table-role-access/initialize": {
            "post": {"tags": ["Access Control"], "summary": "Initialize all table×role access (all granted)", "security": _BEARER, "responses": {"200": _ok()}}
        },
        "/api/auth-config/table-role-access/update": {
            "post": {
                "tags": ["Access Control"], "summary": "Grant/revoke a role's access to a table", "security": _BEARER,
                "parameters": [_json_body("payload", {
                    "table_name": _str("complaint"), "role_id": _int(2), "has_access": _bool(True)},
                    required=["table_name", "role_id", "has_access"])],
                "responses": {"200": _ok()},
            }
        },

        # ---------------- Auth Config ---------------- #
        "/api/auth-config/config": {
            "get": {"tags": ["Auth Config"], "summary": "Get SOURCE auth table/field mappings", "security": _BEARER, "responses": {"200": _ok()}},
            "post": {"tags": ["Auth Config"], "summary": "Update SOURCE auth mappings", "security": _BEARER,
                     "parameters": [_json_body("payload", {
                         "users_table": _str("users"), "username_field": _str("email"),
                         "password_field": _str("password"), "company_table": _str("company"),
                         "company_id_field": _str("id"), "company_name_field": _str("name")})],
                     "responses": {"200": _ok()}},
        },
        "/api/auth-config/security": {
            "get": {"tags": ["Auth Config"], "summary": "Get auth security settings", "security": _BEARER, "responses": {"200": _ok()}},
            "post": {"tags": ["Auth Config"], "summary": "Update auth security settings", "security": _BEARER,
                     "parameters": [_json_body("payload", {"sql_banned_keywords": _str("password,secret,token")})],
                     "responses": {"200": _ok()}},
        },
        "/api/auth-config/source-tables": {
            "get": {"tags": ["Auth Config"], "summary": "List SOURCE database tables", "security": _BEARER, "responses": {"200": _ok()}}
        },
        "/api/auth-config/source-columns/{table_name}": {
            "get": {"tags": ["Auth Config"], "summary": "List columns for a SOURCE table", "security": _BEARER,
                    "parameters": [_path_param("table_name")], "responses": {"200": _ok()}}
        },
        "/api/auth-config/verify": {
            "post": {"tags": ["Auth Config"], "summary": "Verify the auth configuration", "security": _BEARER, "responses": {"200": _ok()}}
        },
        "/api/auth-config/test-user-auth": {
            "post": {"tags": ["Auth Config"], "summary": "Test authenticating a SOURCE user", "security": _BEARER,
                     "parameters": [_json_body("payload", {"email": _str("user@example.com"), "password": _str("secret")})],
                     "responses": {"200": _ok()}},
        },

        # ---------------- Security ---------------- #
        "/api/security/commands": {
            "get": {"tags": ["Security"], "summary": "List restricted SQL commands", "security": _BEARER, "responses": {"200": _ok()}},
            "post": {"tags": ["Security"], "summary": "Add a restricted SQL command", "security": _BEARER,
                     "parameters": [_json_body("payload", {"command": _str("DROP"), "is_blocked": _bool(True)}, required=["command"])],
                     "responses": {"200": _ok()}},
        },
        "/api/security/commands/{cmd_id}": {
            "patch": {"tags": ["Security"], "summary": "Update a restricted command", "security": _BEARER,
                      "parameters": [_path_param("cmd_id", ptype="integer"),
                                     _json_body("payload", {"is_blocked": _bool(False)})], "responses": {"200": _ok()}},
            "delete": {"tags": ["Security"], "summary": "Delete a restricted command", "security": _BEARER,
                       "parameters": [_path_param("cmd_id", ptype="integer")], "responses": {"200": _ok()}},
        },
        "/api/security/keywords": {
            "get": {"tags": ["Security"], "summary": "Get banned keywords", "security": _BEARER, "responses": {"200": _ok()}},
            "post": {"tags": ["Security"], "summary": "Set banned keywords", "security": _BEARER,
                     "parameters": [_json_body("payload", {"keywords": {"type": "array", "items": {"type": "string"}}})],
                     "responses": {"200": _ok()}},
        },

        # ---------------- Cache & Audit ---------------- #
        "/api/cache/metrics": {
            "get": {"tags": ["Cache & Audit"], "summary": "Query metrics summary", "security": _BEARER, "responses": {"200": _ok()}}
        },
        "/api/cache/recent": {
            "get": {"tags": ["Cache & Audit"], "summary": "Recent queries", "security": _BEARER,
                    "parameters": [_query_param("limit", "Max rows", "integer")], "responses": {"200": _ok()}}
        },
        "/api/cache/audit-logs": {
            "get": {"tags": ["Cache & Audit"], "summary": "List audit logs", "security": _BEARER,
                    "parameters": [_query_param("limit", "Max rows", "integer"),
                                   _query_param("is_api", "Filter API-originated", "boolean")],
                    "responses": {"200": _ok()}}
        },
        "/api/cache/audit-logs/{audit_id}": {
            "get": {"tags": ["Cache & Audit"], "summary": "Get one audit log with details", "security": _BEARER,
                    "parameters": [_path_param("audit_id", ptype="integer")], "responses": {"200": _ok(), "404": _err("Not found.")}}
        },

        # ---------------- Data Exchange ---------------- #
        "/api/data-exchange/export": {
            "get": {"tags": ["Data Exchange"], "summary": "Export training/config data", "security": _BEARER, "responses": {"200": _ok()}}
        },
        "/api/data-exchange/preview": {
            "post": {"tags": ["Data Exchange"], "summary": "Preview an import payload", "security": _BEARER,
                     "parameters": [_json_body("payload", {"data": {"type": "object"}})], "responses": {"200": _ok()}}
        },
        "/api/data-exchange/import": {
            "post": {"tags": ["Data Exchange"], "summary": "Import training/config data", "security": _BEARER,
                     "parameters": [_json_body("payload", {"data": {"type": "object"}})], "responses": {"200": _ok()}}
        },
        "/api/data-exchange/database/export": {
            "post": {
                "tags": ["Data Exchange"],
                "summary": "Export entire SQLite database as JSON or SQL",
                "description": "Admin-only. Exports all tables, schema, and data from the admin database.",
                "security": _BEARER,
                "parameters": [_json_body("payload", {
                    "format": _str("json", "Export format: json (default) or sql"),
                    "exclude_tables": {"type": "array", "items": _str(), "description": "Tables to exclude"},
                    "pretty": _bool(False, "Pretty-print JSON output")
                })],
                "responses": {
                    "200": _ok("Database exported successfully"),
                    "403": _err("Admin access required"),
                }
            }
        },
        "/api/data-exchange/database/import": {
            "post": {
                "tags": ["Data Exchange"],
                "summary": "Import entire SQLite database from exported JSON",
                "description": "Admin-only. Imports tables and data from exported database. Can merge, replace, or skip duplicates.",
                "security": _BEARER,
                "parameters": [_json_body("payload", {
                    "export_data": {"type": "object", "description": "Exported database JSON"},
                    "strategy": _str("merge", "Import strategy: merge (default), replace, or skip"),
                    "tables": {"type": "array", "items": _str(), "description": "Optional: only import these tables"}
                }, required=["export_data"])],
                "responses": {
                    "200": _ok("Database imported successfully"),
                    "400": _err("Invalid export format"),
                    "403": _err("Admin access required"),
                }
            }
        },

        # ---------------- System Admin ---------------- #
        "/api/system/status": {
            "get": {
                "tags": ["System Admin"],
                "summary": "Get system status",
                "description": "Admin-only. Returns current server process info and port.",
                "security": _BEARER,
                "responses": {
                    "200": _ok("System status retrieved"),
                    "403": _err("Admin access required"),
                }
            }
        },
        "/api/system/restart": {
            "post": {
                "tags": ["System Admin"],
                "summary": "Restart the Flask backend server",
                "description": "Admin-only. Gracefully restarts the Flask application. Server will reconnect within 2-3 seconds.",
                "security": _BEARER,
                "responses": {
                    "200": _ok("Server restart initiated"),
                    "403": _err("Admin access required"),
                    "500": _err("Restart failed"),
                }
            }
        },
        "/api/system/logs": {
            "get": {
                "tags": ["System Admin"],
                "summary": "Get server logs from last N minutes",
                "description": "Admin-only. Returns Python application logs from the last N minutes (default: 10). Automatically cleans up old logs.",
                "security": _BEARER,
                "parameters": [_query_param("minutes", "Log history in minutes (1-120, default: 10)", "integer")],
                "responses": {
                    "200": _ok("Server logs retrieved"),
                    "403": _err("Admin access required"),
                }
            }
        },
        "/api/system/logs/stats": {
            "get": {
                "tags": ["System Admin"],
                "summary": "Get log file statistics",
                "description": "Admin-only. Returns information about the log file (size, line count, etc).",
                "security": _BEARER,
                "responses": {
                    "200": _ok("Log statistics retrieved"),
                    "403": _err("Admin access required"),
                }
            }
        },
    }


def build_swagger_template():
    """Return the curated Swagger 2.0 spec for the whole API."""
    return {
        "swagger": "2.0",
        "info": {
            "title": "assistantai API",
            "description": (
                "Conversational text-to-SQL analytics API.\n\n"
                "**Authentication** — send `Authorization: Bearer <token>`. Tokens come from "
                "`/api/auth/login` (internal), `/api/auth/token-login` (external JWT exchange), "
                "or a microservice-issued JWT when `MICROSERVICE_MODE=true`.\n\n"
                "**Data isolation** — non-admin requests are automatically scoped to the caller's "
                "company via a mandatory `company_fk` filter (parent company id plus its child "
                "branches), resolved from the SOURCE database. Admins bypass scoping."
            ),
            "version": API_VERSION,
        },
        "basePath": "/",
        "schemes": ["http", "https"],
        "consumes": ["application/json"],
        "produces": ["application/json"],
        "securityDefinitions": _SECURITY_DEFINITIONS,
        "tags": _TAGS,
        "paths": _build_paths(),
    }


def init_swagger(app):
    """Mount Swagger UI at /api/docs/ and the raw spec at /api/openapi.json with authentication."""
    from flask import Blueprint, redirect, url_for
    from ..auth import require_auth
    
    # Create a blueprint to hold protected Swagger routes
    swagger_bp = Blueprint('swagger_protected', __name__)
    
    # Initialize Swagger first without mounting (we'll handle routing ourselves)
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": "openapi_spec",
                "route": "/api/openapi.json",
                "url": "/api/openapi.json",
                "title": "assistantai API",
                "rule_filter": lambda rule: False,
                "model_filter": lambda tag: True,
            }
        ],
        "swagger_ui": False,  # Disable Flasgger's UI - we'll serve our own
        "specs_route": "/api/docs/",
        "use_cdn": False,
    }
    
    # Initialize Swagger (this mounts at default routes, but we'll wrap them)
    swagger = Swagger(app, template=build_swagger_template(), config=swagger_config)
    
    # HTML login page to serve when not authenticated
    LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API Documentation Login</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0;
        }
        .login-container {
            background: white;
            border-radius: 8px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
            width: 100%;
            max-width: 400px;
            padding: 40px;
        }
        .login-header {
            text-align: center;
            margin-bottom: 30px;
        }
        .login-header h1 {
            margin: 0;
            color: #333;
            font-size: 24px;
            font-weight: 600;
        }
        .login-header p {
            margin: 10px 0 0 0;
            color: #666;
            font-size: 14px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 500;
            font-size: 14px;
        }
        .form-group input {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            box-sizing: border-box;
            transition: border-color 0.3s;
        }
        .form-group input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        .login-button {
            width: 100%;
            padding: 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .login-button:hover {
            transform: translateY(-2px);
        }
        .login-button:active {
            transform: translateY(0);
        }
        .login-button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        .error-message {
            display: none;
            background: #fee;
            color: #c33;
            padding: 12px;
            border-radius: 4px;
            margin-bottom: 20px;
            font-size: 14px;
            border: 1px solid #fcc;
        }
        .loading-spinner {
            display: none;
            width: 14px;
            height: 14px;
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-top-color: white;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin-right: 8px;
            vertical-align: middle;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        .info-text {
            color: #666;
            font-size: 12px;
            margin-top: 15px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-header">
            <h1>API Documentation</h1>
            <p>Sign in to access Swagger UI</p>
        </div>
        
        <div id="errorMessage" class="error-message"></div>
        
        <form id="loginForm">
            <div class="form-group">
                <label for="email">Email or Username</label>
                <input 
                    type="text" 
                    id="email" 
                    name="email" 
                    placeholder="enter your email or username" 
                    required 
                    autofocus
                >
            </div>
            
            <div class="form-group">
                <label for="password">Password</label>
                <input 
                    type="password" 
                    id="password" 
                    name="password" 
                    placeholder="Enter your password" 
                    required
                >
            </div>
            
            <button type="submit" class="login-button">
                <span class="loading-spinner" id="spinner"></span>
                <span id="buttonText">Sign In</span>
            </button>
        </form>
        
        <div class="info-text">
            After logging in, you'll be redirected to the API documentation.
        </div>
    </div>

    <script>
        const form = document.getElementById('loginForm');
        const emailInput = document.getElementById('email');
        const passwordInput = document.getElementById('password');
        const errorDiv = document.getElementById('errorMessage');
        const spinner = document.getElementById('spinner');
        const buttonText = document.getElementById('buttonText');
        const submitBtn = form.querySelector('button[type="submit"]');

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // Reset error
            errorDiv.style.display = 'none';
            errorDiv.textContent = '';
            
            // Show loading state
            spinner.style.display = 'inline-block';
            buttonText.textContent = 'Signing in...';
            submitBtn.disabled = true;

            try {
                const response = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        username: emailInput.value,
                        password: passwordInput.value,
                    }),
                    credentials: 'include', // Include cookies
                });

                const data = await response.json();

                if (response.ok && data.success && data.token) {
                    // Store token in localStorage for Swagger UI to use
                    localStorage.setItem('api_token', data.token);
                    // Redirect to /api/docs/ after successful login
                    window.location.href = '/api/docs/';
                } else {
                    // Show error message
                    errorDiv.textContent = data.error || 'Login failed. Please try again.';
                    errorDiv.style.display = 'block';
                    passwordInput.value = '';
                    passwordInput.focus();
                }
            } catch (error) {
                errorDiv.textContent = 'Network error. Please try again.';
                errorDiv.style.display = 'block';
                console.error('Login error:', error);
            } finally {
                // Restore button state
                spinner.style.display = 'none';
                buttonText.textContent = 'Sign In';
                submitBtn.disabled = false;
            }
        });

        // Focus management
        emailInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') passwordInput.focus();
        });
    </script>
</body>
</html>"""
    
    # Now add authentication protection via before_request hook
    @app.before_request
    def protect_swagger_routes():
        """Require authentication to access Swagger UI and OpenAPI spec."""
        from flask import request, jsonify, make_response
        from ..auth import _extract_token, decode_token
        from ..models import User
        import jwt
        
        # Check if this is a Swagger-related route
        is_swagger_route = (
            request.path.startswith('/api/docs') or
            request.path.startswith('/flasgger_static') or
            request.path == '/api/openapi.json'
        )
        
        if is_swagger_route:
            # Try to extract token from Authorization header first
            token = _extract_token()
            
            # If no Authorization header, check cookies
            if not token:
                token = request.cookies.get('auth_token')
            
            if not token:
                # No token found - show login page for HTML requests, JSON error for API requests
                # Check if this is an API request (requesting JSON) vs browser request (requesting HTML)
                is_api_request = (request.path == '/api/openapi.json' or 
                                 'application/json' in request.headers.get('Accept', '') or
                                 request.content_type == 'application/json')
                
                if is_api_request:
                    # API request - return JSON
                    return jsonify({"success": False, "error": "Authentication required. Please login first."}), 401
                else:
                    # Browser request - return HTML login page
                    response = make_response(LOGIN_HTML, 401)
                    response.headers['Content-Type'] = 'text/html; charset=utf-8'
                    return response
            
            try:
                payload = decode_token(token)
                user = User.query.get(int(payload.get("sub", 0)))
                if not user or not user.is_active:
                    # User not found or inactive - show login page
                    is_api_request = (request.path == '/api/openapi.json' or 
                                     'application/json' in request.headers.get('Accept', ''))
                    
                    if is_api_request:
                        return jsonify({"success": False, "error": "User not found or inactive"}), 401
                    else:
                        response = make_response(LOGIN_HTML, 401)
                        response.headers['Content-Type'] = 'text/html; charset=utf-8'
                        return response
            except jwt.ExpiredSignatureError:
                # Token expired - clear cookie and show login page
                is_api_request = (request.path == '/api/openapi.json' or 
                                 'application/json' in request.headers.get('Accept', ''))
                
                if is_api_request:
                    return jsonify({"success": False, "error": "Token expired. Please login again."}), 401
                else:
                    response = make_response(LOGIN_HTML, 401)
                    response.headers['Content-Type'] = 'text/html; charset=utf-8'
                    response.delete_cookie('auth_token')
                    return response
            except Exception as exc:
                # Invalid token - show login page
                is_api_request = (request.path == '/api/openapi.json' or 
                                 'application/json' in request.headers.get('Accept', ''))
                
                if is_api_request:
                    return jsonify({"success": False, "error": f"Invalid token: {str(exc)}"}), 401
                else:
                    response = make_response(LOGIN_HTML, 401)
                    response.headers['Content-Type'] = 'text/html; charset=utf-8'
                    return response
    
    # Add a custom route to serve a working Swagger UI HTML (overrides Flasgger's default)
    # This ensures SwaggerUI loads properly from CDN without template rendering issues
    @app.route('/api/docs/')
    def swagger_ui_custom():
        """Serve a custom Swagger UI HTML that loads from jsDelivr CDN."""
        from flask import request, make_response
        from ..auth import _extract_token, decode_token
        from ..models import User
        import jwt
        
        # Check authentication
        token = _extract_token() or request.cookies.get('auth_token')
        
        if not token:
            response = make_response(LOGIN_HTML, 401)
            response.headers['Content-Type'] = 'text/html; charset=utf-8'
            return response
        
        try:
            payload = decode_token(token)
            user = User.query.get(int(payload.get("sub", 0)))
            if not user or not user.is_active:
                response = make_response(LOGIN_HTML, 401)
                response.headers['Content-Type'] = 'text/html; charset=utf-8'
                return response
        except:
            response = make_response(LOGIN_HTML, 401)
            response.headers['Content-Type'] = 'text/html; charset=utf-8'
            return response
        
        # User is authenticated - serve Swagger UI
        swagger_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>assistantai API Docs</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui.css">
            <style>
                html {
                    box-sizing: border-box;
                    overflow: -moz-scrollbars-vertical;
                    overflow-y: scroll;
                }
                *,
                *:before,
                *:after {
                    box-sizing: inherit;
                }
                body {
                    margin: 0;
                    padding: 0;
                }
                .logout-container {
                    position: fixed;
                    top: 15px;
                    right: 15px;
                    z-index: 1000;
                }
                .logout-btn {
                    background: #ff6b6b;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-size: 14px;
                    font-weight: 500;
                    cursor: pointer;
                    transition: background 0.2s;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
                }
                .logout-btn:hover {
                    background: #ff5252;
                }
                .logout-btn:active {
                    transform: scale(0.98);
                }
            </style>
        </head>
        <body>
            <div class="logout-container">
                <button class="logout-btn" id="logoutBtn">Logout</button>
            </div>
            <div id="swagger-ui"></div>
            <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui-bundle.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui-standalone-preset.js"></script>
            <script>
            window.onload = function() {
                // Set up logout button
                const logoutBtn = document.getElementById('logoutBtn');
                if (logoutBtn) {
                    logoutBtn.addEventListener('click', async function() {
                        try {
                            // Call backend logout endpoint to clear cookie
                            const response = await fetch('/api/auth/logout', {
                                method: 'POST',
                                credentials: 'include'
                            });
                            
                            // Clear localStorage regardless of response
                            localStorage.removeItem('api_token');
                            
                            // Redirect to login page
                            window.location.href = '/api/docs/';
                        } catch (error) {
                            // Even if API call fails, clear localStorage and redirect
                            console.error('Logout error:', error);
                            localStorage.removeItem('api_token');
                            window.location.href = '/api/docs/';
                        }
                    });
                }
                
                // Retrieve token from localStorage
                let authToken = localStorage.getItem('api_token');
                
                // If no localStorage token, try to extract from cookies (set by backend after login)
                if (!authToken) {
                    const cookies = document.cookie.split(';').reduce((acc, c) => {
                        const [key, val] = c.split('=').map(x => x.trim());
                        acc[key] = val;
                        return acc;
                    }, {});
                    authToken = cookies['auth_token'];
                }
                
                // Initialize Swagger UI
                // Note: If we got this page, backend already authenticated the request
                window.ui = SwaggerUIBundle({
                    url: "/api/openapi.json",
                    dom_id: '#swagger-ui',
                    deepLinking: true,
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIStandalonePreset
                    ],
                    plugins: [
                        SwaggerUIBundle.plugins.DownloadUrl
                    ],
                    layout: "StandaloneLayout",
                    // Add request interceptor to include Authorization header with token
                    requestInterceptor: (request) => {
                        if (authToken) {
                            request.headers.Authorization = 'Bearer ' + authToken;
                        }
                        return request;
                    }
                });
            };
            </script>
        </body>
        </html>
        """
        response = make_response(swagger_html, 200)
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
        return response
    
    return app
