# assistantai API Guide

Conversational **text‑to‑SQL** analytics API. This guide covers authentication,
core concepts, and an index of every endpoint. For an always‑accurate, **interactive
reference, use the built‑in Swagger UI** — it is generated from the live server.

| Resource | URL | Authentication |
| --- | --- | --- |
| **Swagger UI (interactive)** | `http://localhost:5174/api/docs/` | ✅ Required |
| **OpenAPI spec (JSON)** | `http://localhost:5174/api/openapi.json` | ✅ Required |
| **Health check** | `http://localhost:5174/api/health` | ❌ Public |

> **Authentication required for Swagger UI:** Only logged-in users can access the API documentation.
> Click **Authorize**, paste `Bearer <token>` (obtained via `/api/auth/login`), and try any endpoint directly.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Authentication](#authentication)
3. [Base URL, Headers & Responses](#base-url-headers--responses)
4. [Multi-Turn Conversations](#multi-turn-conversations)
5. [Company Data Isolation](#company-data-isolation)
6. [Endpoint Reference](#endpoint-reference)
   - [Health & Engine](#health--engine)
   - [Authentication](#authentication-endpoints)
   - [Chat & Query](#chat--query)
   - [Conversations](#conversations)
   - [Training & Knowledge Base](#training--knowledge-base)
   - [Settings](#settings)
   - [Access Control](#access-control)
   - [Auth Config](#auth-config)
   - [Security](#security)
   - [Cache & Audit](#cache--audit)
   - [Data Exchange](#data-exchange)
7. [Error Handling](#error-handling)
8. [Code Examples](#code-examples)

---

## Quick Start

```bash
# 1) Log in to get a JWT
curl -X POST http://localhost:5174/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# 2) Ask a question (token from step 1)
curl -X POST http://localhost:5174/api/chat/query \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "How many complaints did we receive in January?"}'
```

Prefer clicking through requests? Open **`/docs/`** and use **Authorize**.

---

## Authentication

All protected endpoints expect a JWT in the `Authorization` header:

```
Authorization: Bearer <token>
```

There are three ways to obtain a token:

### 1. Internal login — `POST /api/auth/login`
For users stored in the local admin database. Returns a signed JWT.

### 2. External JWT exchange — `POST /api/auth/token-login`
For users authenticated by an upstream service. Send the upstream JWT (containing a
`parentCompanyCode` claim); the API resolves the tenant against the SOURCE database
and returns an internal token whose `company_fk` is the **SOURCE company id**.

```bash
curl -X POST http://localhost:5174/api/auth/token-login \
  -H "Content-Type: application/json" \
  -d '{"token": "eyJhbGciOiJSUzI1NiJ9..."}'
```

### 3. Microservice mode — pass the upstream token directly
When the server runs with `MICROSERVICE_MODE=true`, upstream JWTs are accepted
directly as `Bearer` tokens. Configure validation via environment variables:

```bash
export MICROSERVICE_MODE=true
export MICROSERVICE_TOKEN_ALGORITHM=RS256        # or HS256
export MICROSERVICE_TOKEN_PUBLIC_KEY="<public key>"   # RS256
# or
export MICROSERVICE_TOKEN_SECRET="<shared secret>"    # HS256
```

---

## Base URL, Headers & Responses

- **Base URL:** `http://localhost:5174` (frontend proxy; backend at `http://localhost:5001` is internal only).
- **Headers:** `Content-Type: application/json` for JSON bodies; `Authorization: Bearer <token>` for protected routes.
- **Envelope:** responses use a consistent JSON envelope:

```json
{ "success": true,  "...": "endpoint-specific fields" }
{ "success": false, "error": "Human-readable message" }
```

---

## Multi-Turn Conversations

The API **natively supports multi-turn conversations**. Each conversation maintains full
history and context. Subsequent messages are automatically consolidated and contextualized
with prior turns to generate accurate, contextually-aware SQL queries.

### Continuing a Conversation

To continue an existing conversation, include the `conversation_id` in your request:

```bash
# First message (new conversation)
curl -X POST http://localhost:5001/api/chat/query \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me the top 10 customers by revenue"
  }'
```

Response includes `conversation_id`:
```json
{
  "success": true,
  "conversation_id": "conv_a1b2c3d4e5f6",
  "message": "Here are the top 10 customers...",
  "sql_query": "SELECT ... ORDER BY revenue DESC LIMIT 10",
  "data": [...],
  "row_count": 10
}
```

### Continuing with Follow-up Questions

Use the returned `conversation_id` to send follow-up questions:

```bash
# Second message (continuation of same conversation)
curl -X POST http://localhost:5174/api/chat/query \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How much have they spent this month?",
    "conversation_id": "conv_a1b2c3d4e5f6"
  }'
```

The API will:
1. ✅ Fetch the conversation history
2. ✅ Consolidate your new question with prior context
3. ✅ Generate a SQL query that incorporates the full conversation
4. ✅ Execute and return results
5. ✅ Update the conversation with the new turn

### Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `query` | string | Yes | The natural language question/command |
| `message` | string | Yes* | Alias for `query` (use either one) |
| `conversation_id` | string | No | ID of conversation to continue. If omitted, a new conversation is created |
| `is_first_message` | boolean | No | Override to force marking this as the first message (advanced use only) |

### Examples

**Example 1: Three-turn conversation**

```bash
# Turn 1: Ask initial question
RESPONSE_1=$(curl -X POST http://localhost:5174/api/chat/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the top products by sales?"}')

CONV_ID=$(echo $RESPONSE_1 | jq -r '.conversation_id')

# Turn 2: Follow-up
RESPONSE_2=$(curl -X POST http://localhost:5174/api/chat/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"Show me the trend over the last quarter\", \"conversation_id\": \"$CONV_ID\"}")

# Turn 3: Another follow-up
RESPONSE_3=$(curl -X POST http://localhost:5174/api/chat/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"Compare to last year\", \"conversation_id\": \"$CONV_ID\"}")
```

**Example 2: Context-aware consolidation**

The API automatically understands pronouns and references:

```json
// Turn 1
{ "query": "Show me complaints from January" }
// API runs: SELECT * FROM complaints WHERE MONTH = 1

// Turn 2
{ "query": "Add February too", "conversation_id": "..." }
// API understands "them" = complaints, runs:
// SELECT * FROM complaints WHERE MONTH IN (1, 2)

// Turn 3
{ "query": "How many per category?", "conversation_id": "..." }
// API groups by category and returns breakdown
```

### Retrieving Conversation History

Fetch the full history of a conversation:

```bash
curl -X GET http://localhost:5174/api/conversations/conv_a1b2c3d4e5f6 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Response:
```json
{
  "success": true,
  "conversation": {
    "conversation_id": "conv_a1b2c3d4e5f6",
    "title": "Revenue analysis",
    "created_at": "2026-07-28T10:15:00Z",
    "updated_at": "2026-07-28T10:45:30Z",
    "messages": [
      {
        "type": "user",
        "content": "Show me top customers",
        "ts": "2026-07-28T10:15:00Z",
        "message_position": 1
      },
      {
        "type": "ai",
        "content": "Here are the top 10 customers...",
        "sql_query": "SELECT ...",
        "row_count": 10,
        "ts": "2026-07-28T10:15:02Z",
        "message_position": 1
      },
      {
        "type": "user",
        "content": "How much have they spent?",
        "ts": "2026-07-28T10:20:00Z",
        "message_position": 2
      },
      {
        "type": "ai",
        "content": "Total spend: $...",
        "sql_query": "SELECT ...",
        "row_count": 10,
        "ts": "2026-07-28T10:20:03Z",
        "message_position": 2
      }
    ]
  }
}
```

---

## Company Data Isolation

Non‑admin requests are **automatically scoped** to the caller's organization. The
server derives the tenant's `company_fk` from the token (resolved against the SOURCE
`company` table by `company_code`) and includes the parent company **plus its child
branches**. Every generated/edited query is rewritten to enforce:

```sql
... WHERE company_fk IN (<parent_id>, <branch_id>, ...)
```

- Applied at the SQL boundary on `/api/chat/query`, `/api/chat/run-sql`, and `/api/chat/refresh`.
- Queries that hardcode a different `company_fk` are detected and regenerated.
- **Admins** (`CENTRAL_ADMIN`) bypass scoping and see all data.

---

## Endpoint Reference

> The tables below index every route. Open **`/docs/`** for full request/response schemas and a "Try it out" console.

### Health & Engine

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/api/health` | – | Service + engine status |
| GET | `/api/settings/engine/status` | – | Engine status |
| POST | `/api/settings/engine/reinitialize` | ✓ | Reinitialize the engine |

### Authentication Endpoints

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/api/auth/login` | – | Login (username/email + password) |
| POST | `/api/auth/register` | – | Register an internal user |
| POST | `/api/auth/token-login` | – | Exchange an external JWT for an internal token |
| GET | `/api/auth/me` | ✓ | Current user profile |
| POST | `/api/auth/verify-email` | – | Check an email exists in SOURCE |
| POST | `/api/auth/companies-by-email` | – | List companies for an email |
| POST | `/api/auth/source-db-login` | – | Authenticate against the SOURCE DB |
| POST | `/api/auth/finalize-source-login` | – | Finalize SOURCE login by company |

### Chat & Query

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/api/chat/query` | ✓ | Natural language → SQL → answer |
| POST | `/api/chat/query/guest` | ✓ | Guest‑scoped query |
| POST | `/api/chat/public` | – | **Public docs assistant (no login)** — RAG over public docs, never SQL |
| POST | `/api/chat/run-sql` | ✓ | Execute an edited SELECT (re‑validated) |
| POST | `/api/chat/refresh` | ✓ | Re‑run a previously generated query |

**`POST /api/chat/query`**

```json
{ "query": "How many complaints did we receive in January?", "conversation_id": "conv_123" }
```

Returns the conversational `message`, the `sql_query`, `data`/`row_count`, plus
`visualization`, `trend`, `insights`, and `token_usage`.

**`POST /api/chat/public`** — _no authentication required_

A safe, read‑only assistant for visitors who are **not logged in** (e.g. a landing‑page
or pre‑login help widget). It answers **only** from training **documentation** that is
marked available to non‑logged‑in users (`access = all`) using RAG retrieval. It
**never generates or executes SQL** and never reads the SOURCE database.

```bash
curl -X POST http://localhost:5174/api/chat/public \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I reset my password?"}'
```

Response:

```json
{
  "success": true,
  "mode": "knowledge_base",
  "message": "To reset your password, ...",
  "knowledge_docs_used": 3,
  "sql_query": null,
  "row_count": 0,
  "data": []
}
```

> To make a document answerable here, add it as a **documentation** training item with
> **access = all**. Items marked `authenticated` are excluded from this route.


### Conversations

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/api/conversations` | ✓ | List the user's conversations |
| GET | `/api/conversations/{id}` | ✓ | Get a conversation with messages |
| DELETE | `/api/conversations/{id}` | ✓ | Delete a conversation |
| POST | `/api/conversations/{id}/rename` | ✓ | Rename a conversation |
| PATCH | `/api/conversations/{id}/messages` | ✓ | Update messages |

### Training & Knowledge Base

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/api/training` | ✓ | List training items |
| POST | `/api/training/ddl` | ✓ | Train a DDL statement |
| POST | `/api/training/documentation` | ✓ | Train documentation |
| POST | `/api/training/sql` | ✓ | Train a question → SQL pair |
| POST | `/api/training/auto/information-schema` | ✓ | Auto‑train on INFORMATION_SCHEMA |
| GET | `/api/training/knowledge-base` | ✓ | List knowledge‑base docs |
| POST | `/api/training/knowledge-base/upload` | ✓ | Upload a KB file (pdf/docx/xlsx/pptx/image) |
| PUT/PATCH | `/api/training/{item_id}` | ✓ | Update a training item |
| DELETE | `/api/training/{item_id}` | ✓ | Delete a training item |
| POST | `/api/training/bulk/update` | ✓ | Bulk update items |

### Settings

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET/POST | `/api/settings/llm` | ✓ | Get/update LLM settings |
| GET | `/api/settings/llm/providers` | – | List LLM providers |
| GET/POST | `/api/settings/database` | ✓ | Get/update SOURCE DB settings |
| POST | `/api/settings/database/test` | ✓ | Test a SOURCE DB connection |
| GET | `/api/settings/database/info` | ✓ | SOURCE DB info |
| GET/POST | `/api/settings/vector` | ✓ | Get/update vector store settings |
| GET | `/api/settings/vector/stores` | – | List vector stores |
| GET/POST | `/api/settings/user` | ✓ | Per‑user settings (audio/auto‑speak) |
| GET | `/api/settings/admin-db/info` | ✓ | Admin (local) DB info |
| GET | `/api/settings/microservice/status` | – | Microservice mode status |
| POST | `/api/settings/microservice/verify-token` | ✓ | Verify a microservice JWT |
| POST | `/api/settings/microservice/decode-token` | ✓ | Decode a JWT (no verify) |
| GET | `/api/settings/api-doc` | – | Markdown developer guide |
| GET | `/api/settings/docs` | – | List in‑app docs |
| GET | `/api/settings/docs/{slug}` | – | Get a doc by slug |

> Additional admin‑DB and SQLite management routes exist under `/api/settings/*`; see Swagger UI for the complete list.

### Access Control

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/api/auth-config/table-role-access/tables` | ✓ | List tables with role access |
| GET | `/api/auth-config/table-role-access/roles` | ✓ | List roles |
| POST | `/api/auth-config/table-role-access/initialize` | ✓ | Initialize all table×role access |
| POST | `/api/auth-config/table-role-access/update` | ✓ | Grant/revoke role access to a table |

### Auth Config

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET/POST | `/api/auth-config/config` | ✓ | Get/update SOURCE auth mappings |
| GET/POST | `/api/auth-config/security` | ✓ | Get/update auth security settings |
| GET | `/api/auth-config/source-tables` | ✓ | List SOURCE tables |
| GET | `/api/auth-config/source-columns/{table}` | ✓ | List columns for a SOURCE table |
| POST | `/api/auth-config/verify` | ✓ | Verify the auth configuration |
| POST | `/api/auth-config/test-user-auth` | ✓ | Test SOURCE user authentication |

### Security

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET/POST | `/api/security/commands` | ✓ | List/add restricted SQL commands |
| PATCH/DELETE | `/api/security/commands/{cmd_id}` | ✓ | Update/delete a restricted command |
| GET/POST | `/api/security/keywords` | ✓ | Get/set banned keywords |

### Cache & Audit

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/api/cache/metrics` | ✓ | Query metrics summary |
| GET | `/api/cache/recent` | ✓ | Recent queries |
| GET | `/api/cache/audit-logs` | ✓ | List audit logs |
| GET | `/api/cache/audit-logs/{audit_id}` | ✓ | Get one audit log with details |

### Data Exchange

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/api/data-exchange/export` | ✓ | Export training/config data |
| POST | `/api/data-exchange/preview` | ✓ | Preview an import payload |
| POST | `/api/data-exchange/import` | ✓ | Import training/config data |

---

## Error Handling

| Status | Meaning |
| --- | --- |
| 200 | Success (check the `success` field for logical errors) |
| 400 | Bad request / blocked unsafe SQL / validation error |
| 401 | Missing or invalid token |
| 403 | Authenticated but not allowed (table access / guest restriction) |
| 404 | Resource not found |
| 503 | Engine or SOURCE database not ready |

Error responses always include a message:

```json
{ "success": false, "error": "Authentication required" }
```

---

## Code Examples

### Python (requests)

```python
import requests

BASE = "http://localhost:5174"

# Login
tok = requests.post(f"{BASE}/api/auth/login",
                    json={"username": "admin", "password": "admin123"}).json()["token"]
headers = {"Authorization": f"Bearer {tok}"}

# Query
r = requests.post(f"{BASE}/api/chat/query",
                  json={"query": "How many complaints in January?"},
                  headers=headers).json()
print(r["message"])
print(r["sql_query"], r["row_count"])
```

### JavaScript (fetch)

```javascript
const BASE = "http://localhost:5174";

const { token } = await (await fetch(`${BASE}/api/auth/login`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ username: "admin", password: "admin123" }),
})).json();

const res = await (await fetch(`${BASE}/api/chat/query`, {
  method: "POST",
  headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
  body: JSON.stringify({ query: "How many complaints in January?" }),
})).json();

console.log(res.message, res.sql_query, res.row_count);
```

---

_For the complete, interactive and always up‑to‑date reference, open **`/docs/`** (or visit `http://localhost:5174/docs/`)._
