# API Testing & Implementation Guide - Using POSTMAN with Auth Tokens

**Status:** Complete  
**Last Updated:** June 14, 2026  
**Version:** 1.0

---

## Overview

This guide demonstrates how to test AssistantAI API endpoints using POSTMAN with JWT authentication tokens from your microservice auth server. You'll learn how to configure POSTMAN, send authenticated requests, and interpret responses.

---

## Table of Contents

1. [POSTMAN Setup](#postman-setup)
2. [JWT Token Configuration](#jwt-token-configuration)
3. [Basic API Endpoint Testing](#basic-api-endpoint-testing)
4. [Chat/Query Endpoint (with Auth)](#chatquery-endpoint-with-auth)
5. [Token Verification Endpoints](#token-verification-endpoints)
6. [Full End-to-End Testing Workflow](#full-end-to-end-testing-workflow)
7. [Troubleshooting](#troubleshooting)

---

## POSTMAN Setup

### Step 1: Install POSTMAN

1. Download from [https://www.postman.com/downloads/](https://www.postman.com/downloads/)
2. Install for your operating system (Windows/Mac/Linux)
3. Launch POSTMAN and create a free account

### Step 2: Create a Collection

1. In POSTMAN, click **"Collections"** on the left sidebar
2. Click **"Create Collection"** → Name it: `AssistantAI Auth API Tests`
3. Click **"Create"**

### Step 3: Add Environment Variables

Environments store reusable values like baseURL, tokens, etc.

1. Click the **Settings icon** (⚙️) in top-right
2. Click **"Environments"**
3. Click **"Create"**
4. Name it: `AssistantAI DEV`

**Add these variables:**

| Variable | Initial Value | Current Value |
|----------|---------------|---------------|
| base_url | http://localhost:5001 | http://localhost:5001 |
| token_leelian | [LEELIAN_TOKEN] | eyJhbGciOiJSUzI1NiJ9... |
| token_apin | [APIN_TOKEN] | eyJhbGciOiJSUzI1NiJ9... |
| company_id | [company-uuid] | ea2ec782-1f3b-4856-8ddd |

**Add the token values:**

```
LEELIAN Token (CENTRAL_ADMIN):
eyJhbGciOiJSUzI1NiJ9...

APIN Token (ADMIN):
eyJhbGciOiJSUzI1NiJ9...
```

5. Click **"Save"**

---

## JWT Token Configuration

### Understanding the Tokens

Your two test tokens have these claims:

**LEELIAN Token (CENTRAL_ADMIN):**
```json
{
  "sub": "bepafos767@dusyum.com",
  "userId": "af11775b-616d-4cf9-b9d2-d935d5a302e2",
  "companyName": "LEELIAN",
  "companyType": "PARENT_BRANCH",
  "scopes": "USER",
  "parentCompanyName": "LEELIAN",
  "parentCompanyCode": "ea2ec782-1f3b-4856-8ddd-d55db1323482",
  "iat": 1781446964,
  "exp": 1781482964
}
```
**Role Mapping:** `CENTRAL_ADMIN` → **App Admin (Full Access)**

**APIN Token (ADMIN):**
```json
{
  "sub": "bepafos767@dusyum.com",
  "userId": "af11775b-616d-4cf9-b9d2-d935d5a302e2",
  "companyName": "APIN Medical",
  "companyType": "WORKSPACE",
  "scopes": "USER",
  "parentCompanyName": "APIN Medical",
  "parentCompanyCode": "2219f109-7895-4c6b-b606-f61b0971ab48",
  "iat": 1781447916,
  "exp": 1781483916
}
```
**Role Mapping:** `ADMIN` + company → **Company Admin (Scoped to APIN Medical)**

---

## Basic API Endpoint Testing

### Test 1: Check Microservice Status

**Purpose:** Verify that microservice authentication is enabled

**Request Configuration:**

| Field | Value |
|-------|-------|
| Method | GET |
| URL | {{base_url}}/api/settings/microservice/status |
| Headers | Content-Type: application/json |

**Steps in POSTMAN:**

1. Click **"+"** to create a new request tab
2. Set **Method**: `GET`
3. Set **URL**: `{{base_url}}/api/settings/microservice/status`
4. Click **"Send"**

**Expected Response (200 OK):**

```json
{
  "success": true,
  "microservice_mode": true,
  "token_algorithm": "RS256",
  "has_public_key": true,
  "has_secret": false,
  "message": "Microservice mode is ENABLED"
}
```

---

### Test 2: Decode Token (No Signature Verification)

**Purpose:** Inspect token claims without verifying the signature

**Request Configuration:**

| Field | Value |
|-------|-------|
| Method | POST |
| URL | {{base_url}}/api/settings/microservice/decode-token |
| Auth | Bearer {{token_leelian}} |
| Headers | Content-Type: application/json |

**Steps in POSTMAN:**

1. Create a new **POST** request
2. URL: `{{base_url}}/api/settings/microservice/decode-token`
3. Go to **"Authorization"** tab
4. Select **Type**: `Bearer Token`
5. Token: `{{token_leelian}}`
6. Click **"Send"**

**Expected Response (200 OK):**

```json
{
  "success": true,
  "decoded_claims": {
    "sub": "bepafos767@dusyum.com",
    "userId": "af11775b-616d-4cf9-b9d2-d935d5a302e2",
    "companyName": "LEELIAN",
    "companyType": "PARENT_BRANCH",
    "scopes": "USER",
    "parentCompanyName": "LEELIAN",
    "parentCompanyCode": "ea2ec782-1f3b-4856-8ddd-d55db1323482",
    "iat": 1781446964,
    "exp": 1781482964
  },
  "warning": "⚠️  Signature was NOT verified - for debugging only!"
}
```

---

### Test 3: Verify Token (With Signature Verification)

**Purpose:** Validate JWT signature and extract verified user context

**Request Configuration:**

| Field | Value |
|-------|-------|
| Method | POST |
| URL | {{base_url}}/api/settings/microservice/verify-token |
| Auth | Bearer {{token_leelian}} |
| Headers | Content-Type: application/json |

**Steps in POSTMAN:**

1. Create a new **POST** request
2. URL: `{{base_url}}/api/settings/microservice/verify-token`
3. Go to **"Authorization"** tab
4. Select **Type**: `Bearer Token`
5. Token: `{{token_leelian}}`
6. Click **"Send"**

**Expected Response (200 OK) - LEELIAN Token:**

```json
{
  "success": true,
  "user_context": {
    "email": "bepafos767@dusyum.com",
    "userId": "af11775b-616d-4cf9-b9d2-d935d5a302e2",
    "app_role": "Admin",
    "is_admin": true,
    "is_company_admin": false,
    "access_scope": "global",
    "company_scoped": false,
    "raw_payload": { ... }
  },
  "message": "✅ Token verified for user: bepafos767@dusyum.com"
}
```

**Response for APIN Token (Company Admin):**

```json
{
  "success": true,
  "user_context": {
    "email": "bepafos767@dusyum.com",
    "userId": "af11775b-616d-4cf9-b9d2-d935d5a302e2",
    "app_role": "Company Admin",
    "is_admin": false,
    "is_company_admin": true,
    "access_scope": "2219f109-7895-4c6b-b606-f61b0971ab48",
    "company_scoped": true,
    "company_name": "APIN Medical",
    "raw_payload": { ... }
  },
  "message": "✅ Token verified for user: bepafos767@dusyum.com"
}
```

---

## Chat/Query Endpoint (with Auth)

### Send a Query to Chat API

**Purpose:** Send a natural language query to the assistant and get a SQL-generated response

**Important:** The backend respects role-based access:
- **CENTRAL_ADMIN**: Can query any database, see all companies' data
- **ADMIN (Company-scoped)**: Can only query databases for their assigned company
- **USER**: Limited query access

**Request Configuration:**

| Field | Value |
|-------|-------|
| Method | POST |
| URL | {{base_url}}/api/chat/query |
| Auth | Bearer {{token_leelian}} |
| Content-Type | application/json |
| Body | See below |

### Example 1: Start New Conversation

**Request Body (Omit conversation_id to start new):**

```json
{
  "message": "Show me the top 5 customers by revenue"
}
```

**Response includes conversation_id:**

```json
{
  "success": true,
  "conversation_id": "conv_a1b2c3d4e5f6",
  "message": "Here's the top 5 customers by revenue:",
  "sql_query": "SELECT customer_name, SUM(amount) as total_revenue FROM orders GROUP BY customer_name ORDER BY total_revenue DESC LIMIT 5",
  "data": [
    { "customer_name": "Acme Corp", "total_revenue": 150000 },
    { "customer_name": "TechStarts Inc", "total_revenue": 125000 },
    { "customer_name": "Global Trade Ltd", "total_revenue": 98500 },
    { "customer_name": "Local Services", "total_revenue": 75000 },
    { "customer_name": "Mini Mart", "total_revenue": 45000 }
  ],
  "visualization": {
    "type": "bar",
    "title": "Top 5 Customers by Revenue",
    "data": [ ... ]
  }
}
```

### Example 2: Continue Conversation

**⚠️ IMPORTANT:** Use the `conversation_id` from the previous response to continue the conversation

**Request Body (With conversation_id for follow-up):**

```json
{
  "message": "What was the revenue trend for Acme Corp over the last 12 months?",
  "conversation_id": "conv_a1b2c3d4e5f6"
}
```

**Response:**

```json
{
  "success": true,
  "conversation_id": "conv_a1b2c3d4e5f6",
  "message": "Based on our previous query about top customers, Acme Corp's revenue trend shows...",
  "sql_query": "SELECT DATE_TRUNC('month', order_date) as month, SUM(amount) as monthly_revenue FROM orders WHERE customer_name='Acme Corp' GROUP BY month ORDER BY month DESC LIMIT 12",
  "data": [ ... ],
  "visualization": {
    "type": "line",
    "title": "Acme Corp Revenue Trend (12 months)"
  }
}
```

**Steps in POSTMAN:**

1. Create a new **POST** request
2. URL: `{{base_url}}/api/chat/query`
3. Go to **Authorization** tab → **Bearer Token** → `{{token_leelian}}`
4. Go to **Body** tab → Select **raw** → **JSON**
5. Enter the request body (see above examples)
6. Click **"Send"**
7. **SAVE the conversation_id** from response to use in next request

**Conversation Persistence Rules:**

| Scenario | conversation_id | Behavior |
|----------|-----------------|----------|
| First message | omit or `null` | New conversation created, returns `conversation_id` |
| Follow-up | `"conv_a1b2c3d4e5f6"` | Continues with context from previous messages |
| Switch conversation | different `conversation_id` | Loads different conversation history |
| Start fresh | omit again | Creates brand new conversation |

**Access Control Examples:**

**✅ CENTRAL_ADMIN (LEELIAN token):**
- Can query any database
- Sees results from all companies
- Access scope: `global`

**⚠️ COMPANY_ADMIN (APIN token):**
- Can query only APIN Medical's database
- Sees only APIN Medical company data
- Access scope: `2219f109-7895-4c6b-b606-f61b0971ab48`
- Response includes: `"company_id": "2219f109-7895-4c6b-b606-f61b0971ab48"`

**❌ If user tries to access different company data:**
```json
{
  "success": false,
  "error": "Access denied: Your access is scoped to company APIN Medical only",
  "error_code": "COMPANY_SCOPE_VIOLATION"
}
```

---

## Audit Logs Endpoint

### Retrieve and Filter Audit Logs

**Purpose:** Track all API and UI requests, view success/failure status, and monitor API usage

**Request Configuration:**

| Field | Value |
|-------|-------|
| Method | GET |
| URL | {{base_url}}/api/cache/audit-logs |
| Auth | Bearer Token |
| Query Params | See below |

### Filter Audit Logs

**Query Parameters:**

| Parameter | Type | Example | Description |
|-----------|------|---------|-------------|
| `limit` | number | `?limit=50` | Max results (default: 50, max: 200) |
| `offset` | number | `?offset=100` | Pagination offset |
| `is_api` | boolean | `?is_api=true` | Filter by API requests (true/false) |
| `conversation_id` | string | `?conversation_id=conv_abc123` | Filter by conversation |
| `success` | boolean | `?success=true` | Filter by success status |
| `search` | string | `?search=revenue` | Search in query text |
| `sort` | string | `?sort=-created_at` | Sort field (prefix `-` for desc) |

### Example Requests

**Request 1: Get all API requests (Postman/curl):**
```
GET {{base_url}}/api/cache/audit-logs?is_api=true&limit=20
Authorization: Bearer {{token_leelian}}
```

**Request 2: Get failed requests from specific conversation:**
```
GET {{base_url}}/api/cache/audit-logs?success=false&conversation_id=conv_a1b2c3d4e5f6&limit=10
Authorization: Bearer {{token_leelian}}
```

**Request 3: Search and paginate:**
```
GET {{base_url}}/api/cache/audit-logs?search=customers&limit=25&offset=50&sort=-created_at
Authorization: Bearer {{token_leelian}}
```

**Response (200 OK):**

```json
{
  "success": true,
  "items": [
    {
      "id": 1,
      "conversation_id": "conv_a1b2c3d4e5f6",
      "user_query": "Show me top customers",
      "rewritten_query": "Which customers have highest revenue",
      "generated_sql": "SELECT customer_name, SUM(amount) FROM orders GROUP BY customer_name ORDER BY SUM(amount) DESC LIMIT 10",
      "success": true,
      "is_api": true,
      "user_id": 42,
      "created_at": "2025-01-15T14:32:10.000Z",
      "token_input": 245,
      "token_output": 189,
      "cache_read_tokens": 512,
      "duration_ms": 1850
    }
  ],
  "total": 1250,
  "limit": 20,
  "offset": 0,
  "hasMore": true
}
```

**Response Fields:**

| Field | Description |
|-------|-------------|
| `id` | Unique audit log ID |
| `conversation_id` | Associated conversation ID |
| `user_query` | Original user question |
| `rewritten_query` | AI clarification of the question |
| `generated_sql` | SQL generated by AI |
| `success` | Request succeeded (true/false) |
| `is_api` | true = API request, false = Web UI request |
| `user_id` | ID of user who made request |
| `created_at` | ISO timestamp of request |
| `token_input` | Input tokens consumed by LLM |
| `token_output` | Output tokens generated by LLM |
| `cache_read_tokens` | Tokens read from cache (prompt caching) |
| `duration_ms` | Request duration in milliseconds |

---

## Token Verification Endpoints

### Error Cases

**Case 1: Invalid Token**

Request:
```
POST {{base_url}}/api/settings/microservice/verify-token
Authorization: Bearer invalid_token_here
```

Response (401 Unauthorized):
```json
{
  "success": false,
  "error": "Token verification failed or token expired",
  "debug_info": "Check token validity and algorithm configuration"
}
```

**Case 2: Expired Token**

Response (401 Unauthorized):
```json
{
  "success": false,
  "error": "Token has expired",
  "debug_info": "Refresh token from auth server"
}
```

**Case 3: No Token Provided**

Request:
```
POST {{base_url}}/api/settings/microservice/verify-token
```

Response (400 Bad Request):
```json
{
  "success": false,
  "error": "No token provided. Use Authorization header, JSON body, or form data."
}
```

---

## Full End-to-End Testing Workflow

### Complete Test Scenario

This demonstrates a realistic workflow using both tokens:

**Step 1: Admin User (CENTRAL_ADMIN) Checks System Status**

```
GET {{base_url}}/api/settings/microservice/status
Auth: Bearer {{token_leelian}}

Response:
{
  "success": true,
  "microservice_mode": true,
  "token_algorithm": "RS256",
  "has_public_key": true,
  "message": "Microservice mode is ENABLED"
}
```

**Step 2: Admin Verifies Their Token**

```
POST {{base_url}}/api/settings/microservice/verify-token
Auth: Bearer {{token_leelian}}

Response:
{
  "success": true,
  "user_context": {
    "email": "bepafos767@dusyum.com",
    "app_role": "Admin",
    "is_admin": true,
    "access_scope": "global"
  }
}
```

**Step 3: Admin Queries Global Data**

```
POST {{base_url}}/api/chat/query
Auth: Bearer {{token_leelian}}
Body: { "message": "Show all companies in the database" }

Response: Full list of all companies (global access)
```

**Step 4: Company Admin (APIN) Verifies Their Token**

```
POST {{base_url}}/api/settings/microservice/verify-token
Auth: Bearer {{token_apin}}

Response:
{
  "success": true,
  "user_context": {
    "email": "bepafos767@dusyum.com",
    "app_role": "Company Admin",
    "is_admin": false,
    "is_company_admin": true,
    "company_name": "APIN Medical",
    "access_scope": "2219f109-7895-4c6b-b606-f61b0971ab48"
  }
}
```

**Step 5: Company Admin Queries Their Data**

```
POST {{base_url}}/api/chat/query
Auth: Bearer {{token_apin}}
Body: { "message": "Show APIN Medical revenue by department" }

Response: Only APIN Medical data (scoped access)
```

**Step 6: Company Admin Attempts Global Query**

```
POST {{base_url}}/api/chat/query
Auth: Bearer {{token_apin}}
Body: { "message": "Show all companies in the database" }

Response (403 Forbidden):
{
  "success": false,
  "error": "Access denied: Your access is scoped to company APIN Medical only",
  "company_id": "2219f109-7895-4c6b-b606-f61b0971ab48"
}
```

---

## POSTMAN Collections & Pre-requests

### Import Pre-built Collection

To speed up testing, you can use POSTMAN scripts:

**Pre-request Script (runs before each request):**

```javascript
// Automatically set timestamp
pm.environment.set("timestamp", new Date().toISOString());

// Log the request
console.log(`${pm.request.method} ${pm.request.url}`);
```

**Post-response Script (runs after each request):**

```javascript
// Store response status
pm.environment.set("last_status", pm.response.code);

// Log response
console.log(`Response: ${pm.response.code} ${pm.response.reason}`);

// If token verified successfully, extract app_role
if (pm.response.code === 200) {
    let data = pm.response.json();
    if (data.user_context) {
        pm.environment.set("user_app_role", data.user_context.app_role);
        pm.environment.set("user_company", data.user_context.company_name);
    }
}
```

### Run Collection Tests

1. Open your collection: **AssistantAI Auth API Tests**
2. Click the **"▶ Run"** button
3. POSTMAN runs all requests in sequence
4. View results in the **"Test Results"** panel

---

## Troubleshooting

### Issue: "Bearer token is malformed"

**Cause:** Token format is incorrect

**Solution:**
- Verify you have full token (including all dots: `xxx.xxx.xxx`)
- Check for whitespace at start/end of token
- Ensure using **Bearer Token** authorization type

### Issue: "Token verification failed"

**Cause:** Token signature doesn't match public key

**Solution:**
- Verify public key in `.env` matches auth server
- Check token hasn't been modified
- Ensure token is from same auth server

### Issue: "No response from server"

**Cause:** Backend not running or wrong URL

**Solution:**
- Start backend: `cd backend && python run.py`
- Verify URL: `{{base_url}}` should be `http://localhost:5001`
- Check firewall isn't blocking port 5001

### Issue: "401 Unauthorized" on chat endpoint

**Cause:** Role-based access control preventing query

**Solution:**
- For COMPANY_ADMIN: Can only query own company
- For CENTRAL_ADMIN: Can query any company
- Check `access_scope` in token verification response

### Issue: Expired token

**Cause:** Token has reached expiration time

**Solution:**
- Request new token from auth server
- Test tokens expire 10 hours after issue
- Check `exp` field in decoded token

---

## Quick Reference - All Endpoints

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| /api/settings/microservice/status | GET | No | Check microservice mode |
| /api/settings/microservice/decode-token | POST | Bearer | Decode token (no verify) |
| /api/settings/microservice/verify-token | POST | Bearer | Verify token + RBAC |
| /api/chat/query | POST | Bearer | Send query with auth |
| /api/settings/microservice/status | GET | Bearer | Get LLM/DB config |

---

## Response Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Token verified, query executed |
| 400 | Bad Request | Missing token, invalid body |
| 401 | Unauthorized | Invalid token, expired token |
| 403 | Forbidden | Access denied (scoped to different company) |
| 500 | Server Error | Database connection failed |

---

## Common Response Patterns

**All successful responses follow this pattern:**
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed"
}
```

**All error responses follow this pattern:**
```json
{
  "success": false,
  "error": "Description of what failed",
  "error_code": "ERROR_TYPE",
  "debug_info": "Additional context"
}
```

---

## Environment Variables Checklist

Before testing, ensure these variables are set in POSTMAN environment:

- [ ] `base_url` = `http://localhost:5001`
- [ ] `token_leelian` = Full LEELIAN token
- [ ] `token_apin` = Full APIN token
- [ ] `company_id` = APIN company UUID

---

## Next Steps

1. ✅ Set up POSTMAN with tokens
2. ✅ Test microservice status endpoint
3. ✅ Test token verification (both tokens)
4. ✅ Test chat endpoint with both roles
5. ⏳ Test access control (company scoping)
6. ⏳ Implement RBAC in your application

---

**For more information**, see:
- [MICROSERVICE_TOKEN_VERIFICATION.md](MICROSERVICE_TOKEN_VERIFICATION.md) - Complete token documentation
- [MICROSERVICE_API_REFERENCE.md](MICROSERVICE_API_REFERENCE.md) - API reference card
- Backend terminal logs for detailed request/response tracking

---

**Happy Testing! 🚀**
