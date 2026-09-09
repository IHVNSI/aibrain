# Deployment Checklist ✅

## Summary
✅ **Admin Credentials**: Managed exclusively through database (no hardcoded credentials in code)
✅ **Security**: Enforced on app startup
✅ **Configuration**: All sensitive data in environment variables or database

---

## Pre-Deployment (Local Testing)

- [x] Code compiles without errors
- [x] All imports work correctly
- [x] App initializes successfully
- [x] Auth module tests pass
- [x] No hardcoded credentials in source code
- [x] No breaking changes to existing endpoints

---

## Deployment Steps

### Step 1: Backup Database
```bash
cd backend
cp instance/app.db instance/app.db.backup.$(date +%Y%m%d_%H%M%S)
```

### Step 2: Deploy Updated Code
```bash
# Pull latest changes
git pull origin main

# Or manually copy backend files
```

### Step 3: Set Admin Credentials
Admin credentials should be set via:

**Option A: Database Migration (Recommended)**
- Use your deployment automation to set admin password
- Store in secure vault (AWS Secrets Manager, HashiCorp Vault, etc.)

**Option B: Interactive Reset**
```bash
cd backend
python reset_admin.py
# Follow prompts to set admin email and password
```

### Step 4: Verify Login Works
```bash
# Test with admin credentials (from database/vault)
curl -X POST https://your-server/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "<your-secure-password>"}'

# Expected response includes "token": "eyJ..."
```

---

## Post-Deployment Verification

### ✅ Security Verification
```bash
# Verify no hardcoded credentials appear in logs
docker logs <container_id> | grep -i "password"

# Should NOT contain any actual passwords
```

### ✅ Login Verification
```bash
# Verify admin login works
curl -X POST https://your-server/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "<secured-password>"}'

# Extract token from response
TOKEN=$(response.token)
curl -X GET https://your-server/api/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

---

## Rollback Plan (If Needed)

If something goes wrong:

### Option 1: Restore Database Backup
```bash
cd backend
rm instance/app.db
cp instance/app.db.backup.* instance/app.db
# Restart app
```

### Option 2: Revert Code Changes
```bash
git revert <commit-hash>
# Restart app
```

### Option 3: Manual Password Reset
```bash
python reset_admin.py
# Follow prompts to set new admin credentials
```

---

## Testing Matrix

| Test | Command | Expected Result |
|------|---------|-----------------|
| App Init | `python -c "from app import create_app; create_app()"` | No errors |
| Auth Import | `python -c "from app.api.auth import seed_defaults"` | Module loads |
| Login Success | POST /auth/login with valid credentials | 200 OK + token |
| Login Failure | POST /auth/login with invalid credentials | 401 Unauthorized |
| Admin Access | GET /api/auth/me (authenticated as admin) | 200 OK + user data |

---

## Security Best Practices

✅ **DO**:
- Store admin credentials in secure vault (AWS Secrets Manager, etc.)
- Use environment variables for sensitive configuration
- Rotate admin passwords regularly
- Enable audit logging for admin actions
- Use strong passwords (20+ characters recommended)

❌ **DON'T**:
- Store credentials in source code
- Commit .env files with real credentials
- Use default/test credentials in production
- Log passwords in application logs
- Share credentials via email or chat

---

## Completion Checklist

- [ ] Database backed up
- [ ] Code deployed to production
- [ ] Admin credentials set securely (vault/environment)
- [ ] App initialized successfully
- [ ] Admin login verified
- [ ] No hardcoded credentials visible in logs
- [ ] Documentation reviewed by security team
- [ ] Audit logging enabled
- [ ] Access monitoring configured

---

## Sign-Off

- **Deployed By**: _______________
- **Deployment Date**: _______________
- **Verification Status**: _______________
- **Issues**: None / [describe] _______________

---

**Last Updated**: 2026-07-31
**Status**: ✅ Ready for Production
**Risk Level**: 🟢 Low (Backward compatible, auto-enforcement)
