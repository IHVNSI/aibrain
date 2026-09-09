# Using External Auth Token with Company Filtering

## Token Decoded
```json
{
  "aud": "99e9fe82-308b-4d6f-b53a-9a46d92f8d9b",
  "companyName": "IHVN FORMS33",
  "companyType": "PARENT_BRANCH",
  "exp": 1782763828,
  "iat": 1782727828,
  "parentCompanyCode": "99e9fe82-308b-4d6f-b53a-9a46d92f8d9b",
  "parentCompanyName": "IHVN FORMS33",
  "scopes": "USER",
  "sub": "tayoola@seamhealth.com",
  "userId": "b74d9f59-49dc-4074-a40f-c7072cd32535"
}
```

---

## Database Schema Relationships

### Company Structure
```
companies table:
- id (INTEGER PRIMARY KEY) - Internal ID
- name (VARCHAR) - Company name (e.g., "IHVN FORMS33")
- parent_company_id (INTEGER) - Self-referencing FK to parent (NULL if parent)
- company_type (VARCHAR) - "PARENT_COMPANY" or "BRANCH"
```

### User & Company Mapping
```
users table:
- id
- username
- email
- company_id (FK → companies.id)
- branch_id (FK → branches.id)

user_companies table (many-to-many):
- user_id (FK → users.id)
- company_id (FK → companies.id)
- user_role
- joined_at
```

---

## Flow: Token → Company ID → Data Access

### Step 1: Extract Company Code from Token
```
Token claim: parentCompanyCode = "99e9fe82-308b-4d6f-b53a-9a46d92f8d9b"
```

### Step 2: Lookup Company ID in Database
```sql
-- Find the company by name or external code
SELECT id, name, company_type, parent_company_id
FROM companies
WHERE name = 'IHVN FORMS33'  -- or where external_code = 'parent_company_code'
```

### Step 3: Find Related Companies (Branches)
```sql
-- If user belongs to parent company, find all branches
SELECT id, name, company_type, parent_company_id
FROM companies
WHERE parent_company_id = <company_id>
  AND is_active = TRUE
```

### Step 4: Apply Company Filter to All Queries
```sql
-- User can ONLY see data where:
-- (company_fk = <company_id> OR company_id = <company_id>)
-- OR (company_fk IN (branch_ids) OR company_id IN (branch_ids))
```

---

## How the System Extracts Company Information

### Token Claims Processing (in microservice_auth.py)

```python
def _lookup_company_id(company_code: str, company_name: str):
    """
    Converts external company code to internal company_id.
    
    Your token provides:
    - parentCompanyCode: "99e9fe82-308b-4d6f-b53a-9a46d92f8d9b"
    - parentCompanyName: "IHVN FORMS33"
    
    This function looks it up in the companies table.
    """
    # Try lookup by code (external identifier)
    if company_code:
        company = Company.query.filter_by(name=company_code).first()
        if company:
            return company.id  # e.g., 1, 5, 10, etc.
    
    # Fallback: lookup by company name
    if company_name:
        company = Company.query.filter_by(name=company_name).first()
        if company:
            return company.id
    
    return None
```

### Token to User Context Mapping

```python
def _map_token_claims_to_app_roles(claims):
    """
    Maps your token to the application's user context.
    """
    # Extract from your token
    company_name = claims.get("companyName", "")  # "IHVN FORMS33"
    parent_company_name = claims.get("parentCompanyName", "")  # "IHVN FORMS33"
    company_code = claims.get("parentCompanyCode", "")  # "99e9fe82-308b-4d6f-b53a-9a46d92f8d9b"
    scopes = claims.get("scopes", [])  # "USER"
    
    # Lookup in database
    company_id = _lookup_company_id(company_code, company_name or parent_company_name)
    
    # Determine user role
    if "ADMIN" in scopes and company_name:
        return {
            "app_role": "Company Admin",
            "is_admin": False,
            "is_company_admin": True,
            "company_scoped": True,
            "company_id": company_id,
            "company_name": company_name,
        }
    else:
        return {
            "app_role": "User",
            "is_admin": False,
            "is_company_admin": False,
            "company_scoped": True,
            "company_id": company_id,
            "company_name": company_name or parent_company_name,
        }
```

### Result: User Context

```python
{
    "user_id": "b74d9f59-49dc-4074-a40f-c7072cd32535",
    "email": "tayoola@seamhealth.com",
    "company_id": 5,  # ← Resolved from database
    "company_name": "IHVN FORMS33",
    "company_scoped": True,
    "is_admin": False,
    "app_role": "User",
    "roles": ["USER"],
    "scopes": ["USER"],
}
```

---

## Filtering Queries Based on Company

### Direct Database Table Filtering

Your source database tables should have `company_fk` or `company_id` columns:

```sql
-- User's source database tables
CREATE TABLE complaints (
    id INT PRIMARY KEY,
    company_fk INT,  -- ← Filter here
    description TEXT,
    status VARCHAR
);

CREATE TABLE customers (
    id INT PRIMARY KEY,
    company_id INT,  -- ← Or here
    name VARCHAR,
    email VARCHAR
);
```

### Generated SQL Query Filtering

When user asks: "Show me all complaints"

**Before filtering:**
```sql
SELECT * FROM complaints
```

**After company filter applied (by UserQueryFilter):**
```sql
SELECT * FROM complaints
WHERE company_fk = 5  -- ← Only this company's data
```

**For parent company with branches:**
```sql
SELECT * FROM complaints
WHERE company_fk IN (5, 6, 7)  -- ← Parent + branch 1 + branch 2
```

---

## API Implementation Example

### Using the Token in an API Request

```bash
curl -X POST "http://localhost:5001/api/chat/query" \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiJ9.eyJz..." \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "conv123",
    "prompt": "Show me all complaints from this company"
  }'
```

### What Happens Inside

```python
@chat_bp.route("/query", methods=["POST"])
@require_auth
def query():
    # ✅ @require_auth extracts token and creates user context
    ctx = current_user_context()
    
    # ctx now contains:
    # {
    #   "user_id": "b74d9f59-49dc-4074-a40f-c7072cd32535",
    #   "company_id": 5,
    #   "company_scoped": True,
    #   "is_admin": False,
    #   ...
    # }
    
    # Get user's prompt
    user_prompt = request.json.get("prompt")
    
    # Generate SQL using LLM
    sql = llm.generate_sql(user_prompt)
    # Result: "SELECT * FROM complaints"
    
    # ✅ Apply company filter BEFORE execution
    user_filter = UserQueryFilter(
        user_id=ctx.get("user_id"),
        company_id=ctx.get("company_id"),  # 5
        is_admin=ctx.get("is_admin")       # False
    )
    
    filtered_sql = user_filter.modify_sql_query(sql)
    # Result: "SELECT * FROM complaints WHERE company_fk = 5"
    
    # Execute filtered query
    results = execute(filtered_sql)
    # User only sees data from their company
    
    return jsonify({
        "success": True,
        "sql": filtered_sql,
        "data": results,
    })
```

---

## Database Setup for Company Filtering

### 1. Ensure Company Records Exist

```sql
-- Admin database
INSERT INTO companies (id, name, company_type, parent_company_id, is_active)
VALUES (5, 'IHVN FORMS33', 'PARENT_COMPANY', NULL, TRUE);

-- If there are branches
INSERT INTO companies (id, name, company_type, parent_company_id, is_active)
VALUES 
  (6, 'IHVN FORMS33 - Branch 1', 'BRANCH', 5, TRUE),
  (7, 'IHVN FORMS33 - Branch 2', 'BRANCH', 5, TRUE);
```

### 2. User to Company Mapping

```sql
-- Map user to company (if needed in this system)
INSERT INTO user_companies (user_id, company_id, user_role, joined_at)
VALUES (1, 5, 'USER', NOW());
```

### 3. Source Database Filtering Columns

In your source database (the database being queried), ensure tables have:

```sql
-- Option A: company_fk (foreign key style)
ALTER TABLE complaints ADD COLUMN company_fk INT;
ALTER TABLE customers ADD COLUMN company_fk INT;

-- Option B: company_id (direct reference)
ALTER TABLE complaints ADD COLUMN company_id INT;
ALTER TABLE customers ADD COLUMN company_id INT;

-- The system checks for either column name
```

---

## Environment Configuration

### .env File Settings

```bash
# Microservice mode - trust tokens from your auth server
MICROSERVICE_MODE=true

# Token validation (RS256 for RSA public key)
MICROSERVICE_TOKEN_ALGORITHM=RS256
MICROSERVICE_TOKEN_PUBLIC_KEY=<your-rsa-public-key>

# Or for HS256 (symmetric)
MICROSERVICE_TOKEN_ALGORITHM=HS256
MICROSERVICE_TOKEN_SECRET=<your-shared-secret>

# Token introspection (alternative validation method)
MICROSERVICE_TOKEN_INTROSPECTION_URL=https://your-auth-server/api/token/introspect

# Source database to query
SOURCE_DB_URL=postgresql://user:pass@host:5432/your_database
```

---

## Testing the Flow

### Test Request with Your Token

```bash
curl -X POST "http://localhost:5001/api/chat/query" \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ0YXlvb2xhQHNlYW1oZWFsdGguY29tIiwic2NvcGVzIjoiVVNFUiIsInVzZXJJZCI6ImI3NGQ5ZjU5LTQ5ZGMtNDA3NC1hNDBmLWM3MDcyY2QzMjUzNSIsImlhdCI6MTc4MjcyNzgyOCwiZXhwIjoxNzgyNzYzODI4LCJhdWQiOiI5OWU5ZmU4Mi0zMDhiLTRkNmYtYjUzYS05YTQ2ZDkyZjhkOWIiLCJjb21wYW55TmFtZSI6IklIVk4gRk9STVMzMyIsImNvbXBhbnlUeXBlIjoiUEFSRU5UX0JSQU5DSCIsInBhcmVudENvbXBhbnlDb2RlIjoiOTllOWZlODItMzA4Yi00ZDZmLWI1M2EtOWE0NmQ5MmY4ZDliIiwicGFyZW50Q29tcGFueU5hbWUiOiJJSFZOIEZPUk1TMzMifQ.UMJMt2BT0nUOnfuBB9W36bRXkO1H1TyDuWTUZZsMNLk3Gjnfvz9InmpSPo1LN2h1tZ5MDHvPNIdf015QCxuViRb2E0hiAusGXoOujdLeuA6ikj4NMAtAbp9K3RIWNAPPpJ_fPeNc20hlbLAEKsptEOGh4p6TsMxs9TU5MGIx_pX-CYJnFxg87QZ5bNjCw9uqjkRWboW9JavSklI4ZeokM8Nu-u8AgUuUz5aYMQBArWcbrq_421EtQAUQFmQQeE5IY6IBMbqDCqKzWpgERkJHJXnlgTerLgvcOSYNiWVMa9NnXoYnti1xPks6nvRz6OOfnx5JVmqolqo7ymbdm6j34g" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "test-conv-1",
    "prompt": "Show me all complaints"
  }'
```

### Expected Response

```json
{
  "success": true,
  "conversation_id": "test-conv-1",
  "sql_query": "SELECT * FROM complaints WHERE company_fk = 5",
  "data": [
    {
      "id": 1,
      "company_fk": 5,
      "description": "Issue with form",
      "status": "resolved"
    }
  ]
}
```

---

## Key Implementation Points

### ✅ Company Resolution
1. Token has `parentCompanyCode` and `parentCompanyName`
2. System looks up `company_id` in the `companies` table
3. This `company_id` is used for ALL data filtering

### ✅ Related Companies (Parent + Branches)
1. If company has `parent_company_id = NULL`, it's a parent
2. Find branches: `SELECT id FROM companies WHERE parent_company_id = <company_id>`
3. Filter with: `WHERE company_fk IN (parent_id, branch1_id, branch2_id)`

### ✅ Auto-Filtering in UserQueryFilter
The system automatically:
- Intercepts generated SQL
- Adds `WHERE company_fk = X` or `WHERE company_fk IN (X, Y, Z)`
- Executes filtered query
- Returns only company data

### ✅ Multi-Tenant Isolation
- User from Company A CANNOT see Company B data
- Even if they manually edit SQL
- Filter is applied before database execution
- All audit logs show company_id for tracking

---

## Troubleshooting

### Issue: "Company not found"
**Solution:** Ensure company record exists in admin database:
```sql
SELECT * FROM companies WHERE name = 'IHVN FORMS33';
```

### Issue: "No data returned"
**Solution:** Check source database table has company_fk column:
```sql
SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'complaints' AND COLUMN_NAME IN ('company_fk', 'company_id');
```

### Issue: "Unauthorized" error
**Solution:** Check token is valid and not expired:
```bash
# The token exp claim should be > current timestamp
```

---

**Next Steps:**
1. Set `MICROSERVICE_MODE=true` in `.env`
2. Add your RS256 public key or HS256 secret
3. Ensure admin database has company records
4. Start the server: `python run.py`
5. Send request with Authorization header
6. Verify data is filtered by company
