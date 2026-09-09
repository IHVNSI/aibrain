# Postman Guide: Testing Multi-Turn Conversations

This guide walks you through testing the multi-turn conversation feature of the assistantai API using Postman.

## Overview

Multi-turn conversations allow you to have a continuous dialogue where the API remembers previous context. The key is passing the `conversation_id` from the first response in all subsequent messages.

---

## Quick Start (5-minute setup)

### 1. Get Authentication Token

**Endpoint:** `POST http://localhost:5000/api/auth/login`

**Body (JSON):**
```json
{
  "username": "admin",
  "password": "admin"
}
```

**Expected Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "company_fk": 1
  }
}
```

**Copy the `token` value** — you'll use this in all subsequent requests.

---

## Setting Up Postman Variables (Recommended)

To avoid copying/pasting tokens repeatedly, set up Postman variables:

1. Open **Postman** → Click **Environment** (bottom left)
2. Click **Create** → Name it "assistantai-dev"
3. Add these variables:
   ```
   | Variable | Initial Value | Current Value |
   |----------|---------------|---------------|
   | base_url | http://localhost:5000 | http://localhost:5000 |
   | token | (leave empty) | (will auto-populate) |
   | conversation_id | (leave empty) | (will auto-populate) |
   ```
4. Click **Save**

### Auto-populate `token` from login response:

1. Create a **POST** request to `{{base_url}}/api/auth/login`
2. Under **Tests** tab, add:
   ```javascript
   if (pm.response.code === 200) {
       var data = pm.response.json();
       pm.environment.set("token", data.token);
   }
   ```
3. Send the request → token auto-saves to environment

---

## Multi-Turn Conversation Workflow

### Step 1: Start a New Conversation (First Message)

**Endpoint:** `POST {{base_url}}/api/chat/query`

**Headers:**
```
Authorization: Bearer {{token}}
Content-Type: application/json
```

**Body:**
```json
{
  "query": "How many complaints did we receive in January?"
}
```

**Expected Response:**
```json
{
  "conversation_id": "conv_5f8c3a2b1e9d4k7l",
  "response": "Based on the data, you received 42 complaints in January.",
  "sql_query": "SELECT COUNT(*) FROM complaints WHERE MONTH(created_date) = 1 AND YEAR(created_date) = 2024",
  "rows": [
    [42]
  ],
  "mode": "database",
  "analysis": {
    "table_names": ["complaints"],
    "filters_applied": ["MONTH=1", "YEAR=2024"]
  }
}
```

**Save the `conversation_id` for Step 2.**

### Set Conversation ID Variable (Auto-populate):

Under the **Tests** tab of this request, add:
```javascript
if (pm.response.code === 200) {
    var data = pm.response.json();
    pm.environment.set("conversation_id", data.conversation_id);
}
```

Now `{{conversation_id}}` is automatically available for follow-up messages.

---

### Step 2: Continue the Conversation (Follow-up Message)

**Endpoint:** `POST {{base_url}}/api/chat/query`

**Headers:**
```
Authorization: Bearer {{token}}
Content-Type: application/json
```

**Body** (note the `conversation_id`):
```json
{
  "query": "What was the main reason for complaints?",
  "conversation_id": "{{conversation_id}}"
}
```

**Expected Response:**
```json
{
  "conversation_id": "conv_5f8c3a2b1e9d4k7l",
  "response": "The main reasons were: (1) Billing errors (35%), (2) Slow service (40%), (3) Other (25%).",
  "sql_query": "SELECT reason, COUNT(*) as count FROM complaints WHERE MONTH(created_date) = 1 AND YEAR(created_date) = 2024 GROUP BY reason ORDER BY count DESC",
  "rows": [
    ["Slow service", 17],
    ["Billing errors", 14],
    ["Other", 11]
  ],
  "mode": "database"
}
```

**Key point:** The API automatically incorporates the context from the first message ("January complaints") into this follow-up query.

---

### Step 3: Ask a Refinement (Another Follow-up)

**Endpoint:** `POST {{base_url}}/api/chat/query`

**Body:**
```json
{
  "query": "How many of those were resolved?",
  "conversation_id": "{{conversation_id}}"
}
```

**Expected Response:**
```json
{
  "conversation_id": "conv_5f8c3a2b1e9d4k7l",
  "response": "Of the 42 complaints from January, 38 have been resolved (90.5%).",
  "sql_query": "SELECT COUNT(*) FROM complaints WHERE MONTH(created_date) = 1 AND YEAR(created_date) = 2024 AND status = 'resolved'",
  "rows": [
    [38]
  ],
  "mode": "database"
}
```

---

## Advanced: Multi-Turn Conversation Pattern Examples

### Pattern 1: Drill Down into Details

```
Message 1: "Show me Q1 sales by region"
  → conversation_id: conv_abc123

Message 2: "Filter to just the North region"
  → Passes conv_abc123
  → API remembers Q1 + sales context

Message 3: "What are the top 3 products?"
  → Passes conv_abc123
  → API filters within Q1 + North region context
```

### Pattern 2: Comparative Analysis

```
Message 1: "Compare January complaints to February"
  → conversation_id: conv_def456

Message 2: "What's the trend?"
  → Passes conv_def456
  → API analyzes both months' data

Message 3: "Project March based on the trend"
  → Passes conv_def456
  → API uses both months to forecast
```

### Pattern 3: Narrow Down Filters

```
Message 1: "Show complaints from high-value customers"
  → conversation_id: conv_ghi789

Message 2: "Only those from the last 7 days"
  → Passes conv_ghi789

Message 3: "Break it down by region"
  → Passes conv_ghi789
  → Each message adds a filter layer
```

---

## Testing Checklist

Use this checklist to validate multi-turn conversation functionality:

- [ ] **Auth**: Login endpoint returns a token
- [ ] **First Message**: POST to `/api/chat/query` without `conversation_id` creates a new conversation
- [ ] **Response Contains ID**: First response includes `conversation_id` field
- [ ] **Follow-up Works**: Second message with `conversation_id` returns a response
- [ ] **Context Preserved**: Follow-up message references entities from first message
- [ ] **Multiple Follow-ups**: Can send 3+ messages to same conversation without errors
- [ ] **History Accessible**: GET `/api/conversations/{id}` returns all messages in order
- [ ] **Conversation Listing**: GET `/api/conversations` shows the new conversation
- [ ] **Conversation Rename**: PATCH `/api/conversations/{id}/rename` changes title successfully
- [ ] **Conversation Delete**: DELETE `/api/conversations/{id}` removes the conversation

---

## Troubleshooting

### Error: "Unexpected token in JSON"
- Make sure `Content-Type: application/json` is set in Headers
- Verify JSON body is valid (use Postman's JSON validator)

### Error: "Invalid conversation_id"
- Ensure you're passing the **exact** `conversation_id` from the first response
- Check that the conversation hasn't been deleted

### Error: "401 Unauthorized"
- Re-run the login endpoint to get a fresh token
- Make sure the `Authorization: Bearer {{token}}` header is set

### Error: "Engine not ready (503)"
- The text-to-SQL engine hasn't finished initializing
- Wait a few seconds and retry
- Check backend logs for initialization errors

### Response doesn't use previous context
- Verify `conversation_id` is being passed correctly
- Check the API response `mode` field — should be `database` or `knowledge_base`
- Review the generated `sql_query` to see if it includes prior filters

---

## API Reference: Chat Endpoint

### `/api/chat/query` (POST)

**Request Body:**
```json
{
  "query": "Your natural language question",
  "conversation_id": "conv_xyz (optional - omit for new conversation)",
  "is_first_message": false
}
```

**Response:**
```json
{
  "conversation_id": "conv_xyz",
  "response": "Natural language answer",
  "sql_query": "SELECT ... (null if knowledge base only)",
  "rows": [["data", "row"], ...],
  "mode": "database | knowledge_base | direct",
  "analysis": {
    "table_names": ["table1", "table2"],
    "filters_applied": ["filter1", "filter2"]
  }
}
```

**Status Codes:**
- `200` - Success
- `401` - Missing/invalid token
- `403` - Access denied (guest users, table access restrictions)
- `503` - Engine not ready

---

## Conversation Management Endpoints

### List Conversations
```
GET /api/conversations
Authorization: Bearer {{token}}
```

### Get a Specific Conversation
```
GET /api/conversations/{{conversation_id}}
Authorization: Bearer {{token}}
```

### Rename Conversation
```
POST /api/conversations/{{conversation_id}}/rename
Authorization: Bearer {{token}}
Content-Type: application/json

{
  "title": "Q1 Complaint Analysis"
}
```

### Delete Conversation
```
DELETE /api/conversations/{{conversation_id}}
Authorization: Bearer {{token}}
```

---

## Sample Postman Collection Export

Save this as `assistantai-multiturn.json` and import into Postman:

```json
{
  "info": {
    "name": "assistantai Multi-Turn Conversations",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "1. Login",
      "request": {
        "method": "POST",
        "header": [{"key": "Content-Type", "value": "application/json"}],
        "body": {"mode": "raw", "raw": "{\"username\": \"admin\", \"password\": \"admin\"}"},
        "url": {"raw": "{{base_url}}/api/auth/login", "host": ["{{base_url}}"], "path": ["api", "auth", "login"]}
      }
    },
    {
      "name": "2. Start Conversation",
      "request": {
        "method": "POST",
        "header": [
          {"key": "Authorization", "value": "Bearer {{token}}"},
          {"key": "Content-Type", "value": "application/json"}
        ],
        "body": {"mode": "raw", "raw": "{\"query\": \"How many complaints did we receive in January?\"}"},
        "url": {"raw": "{{base_url}}/api/chat/query", "host": ["{{base_url}}"], "path": ["api", "chat", "query"]}
      }
    },
    {
      "name": "3. Follow-up Message",
      "request": {
        "method": "POST",
        "header": [
          {"key": "Authorization", "value": "Bearer {{token}}"},
          {"key": "Content-Type", "value": "application/json"}
        ],
        "body": {"mode": "raw", "raw": "{\"query\": \"What was the main reason?\", \"conversation_id\": \"{{conversation_id}}\"}"},
        "url": {"raw": "{{base_url}}/api/chat/query", "host": ["{{base_url}}"], "path": ["api", "chat", "query"]}
      }
    }
  ]
}
```

---

## Tips for Effective Testing

1. **Use meaningful queries** that reference entities, dates, or concepts so you can verify the context is being used
2. **Check the SQL queries** in responses to confirm they're building on previous filters
3. **Test edge cases**: very short conversations (2 messages), long conversations (10+ messages), mixed content
4. **Monitor backend logs** to see how the conversation context is being processed
5. **Test after configuration changes** (LLM model, database, vector store) to ensure multi-turn still works

---

## Common Use Cases

### Financial Analysis Multi-Turn
```
1. "Show me revenue by month for 2024"
2. "Which month had the highest growth?"
3. "What products drove that growth?"
4. "Compare to the same month in 2023"
```

### Operational Investigation
```
1. "How many orders are delayed?"
2. "What's the main delay reason?"
3. "Which warehouses are affected?"
4. "What's the estimated resolution time?"
```

### Customer Support Dashboard
```
1. "Show tickets created this week"
2. "How many are still open?"
3. "What's the average resolution time?"
4. "Break it down by team"
```

---

## For More Information

- API Documentation: `http://localhost:5000/api/docs/`
- Backend Architecture: See `docs/Code_Structure_Architecture.md`
- Database Migration Guide: See `docs/Database_Migration_Guide.md`
