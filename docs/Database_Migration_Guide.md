# Database Migration Guide

## Overview

The **Admin Database Migration** feature allows you to transfer the admin database from SQLite to PostgreSQL or MySQL directly from the frontend Settings panel. The migration automatically:

1. ✅ Creates a backup of the current database
2. ✅ Creates the target database (if it doesn't exist)
3. ✅ Migrates all data (conversations, settings, training data, audit logs)
4. ✅ Updates the `.env` file with the new database URL
5. ✅ Enforces the change on application restart

## Why Migrate?

### SQLite (Default)
- ✅ Perfect for development and single-user deployments
- ✅ No server setup needed
- ❌ Not suitable for high-concurrency applications
- ❌ Limited to local file storage

### PostgreSQL (Recommended for Production)
- ✅ Excellent for production deployments
- ✅ Supports concurrent connections
- ✅ Advanced query optimization
- ✅ Reliable and battle-tested
- ✅ Easy horizontal scaling

### MySQL (Alternative)
- ✅ Popular and widely supported
- ✅ Good performance for most applications
- ✅ Wide hosting provider support
- ❌ Slightly less advanced than PostgreSQL

## Migration Steps

### Step 1: Access Admin DB Settings

1. Open the application Settings
2. Click the **"Admin DB"** tab
3. Review your current database information

### Step 2: Prepare Target Database

#### Option A: Let the App Create It
1. Enter your database connection details
2. Click **"Create DB"** button
3. App will create the database automatically

#### Option B: Create Manually
1. Create the database on your server manually
2. Verify connectivity in Settings

### Step 3: Test Connection

1. Enter all target database connection details:
   - **Database Type**: PostgreSQL, MySQL, or SQLite
   - **Host**: Database server address
   - **Port**: Database server port
   - **Username**: Database user
   - **Password**: Database password
   - **Database Name**: Target database name

2. Click **"Test Connection"** to verify connectivity

### Step 4: Perform Migration

1. Click **"Migrate Data"** button
2. Review the warning message carefully
3. Confirm the migration
4. Wait for the migration to complete
5. **IMPORTANT**: Restart the application to use the new database

**System will automatically:**
- Create a backup of current database
- Migrate all data to new database
- Update `.env` file with `ADMIN_DB_URL`
- Display migration statistics (tables migrated, rows transferred)

## Connection String Formats

### PostgreSQL
```
postgresql+psycopg2://username:password@hostname:5432/database_name
```

Example:
```
postgresql+psycopg2://app_user:secure_pass@db.example.com:5432/assistantai_admin
```

### MySQL
```
mysql+pymysql://username:password@hostname:3306/database_name
```

Example:
```
mysql+pymysql://app_user:secure_pass@db.example.com:3306/assistantai_admin
```

### SQLite
```
sqlite:///path/to/database.db
```

Example:
```
sqlite:///./assistantai_admin.db
```

## Migration Statistics

After successful migration, you'll see:
- **Tables Migrated**: Number of database tables transferred
- **Rows Transferred**: Total records moved
- **Migration Status**: Success confirmation

## Important Notes

### Before Migration
⚠️ **Always**:
- Test connection before migrating
- Ensure database server is running and accessible
- Create a manual backup if possible
- Notify users that app will be briefly unavailable

### During Migration
- Do NOT restart the application
- Do NOT close the Settings panel
- Wait for "Migration Complete" message
- Monitor the progress message

### After Migration
**CRITICAL**: You must **restart the application** for changes to take effect
- Old database connection will be replaced
- New database will be active on restart
- All data is preserved

## Troubleshooting

### Error: "Cannot connect to target database"

**Causes:**
- Database server not running
- Incorrect host/port
- Firewall blocking connection
- Wrong credentials

**Solutions:**
1. Verify database server is running
2. Test connection from command line:
   ```bash
   # PostgreSQL
   psql -h localhost -U user -d database_name
   
   # MySQL
   mysql -h localhost -u user -p database_name
   ```
3. Check firewall rules
4. Verify credentials

### Error: "Database already exists"

This is usually not an error. The system handles existing databases gracefully and will use them for migration.

### Error: "Permission denied" or "Access denied"

The user doesn't have permission to:
- Create databases
- Access the specified database
- Create tables

**Solution**: 
Use a database user with higher privileges (admin/root)

### Migration hangs or times out

**Causes:**
- Network connectivity issues
- Large database taking time to migrate
- Database server performance issues

**Solution:**
- Ensure stable network connection
- Check database server performance
- Increase timeout in connection settings

## .env File Management

The application automatically manages `.env` file:

```env
# Before Migration
ADMIN_DB_URL=sqlite:///assistantai.db

# After Migration to PostgreSQL
ADMIN_DB_URL=postgresql+psycopg2://user:pass@host:5432/assistantai_admin

# After Migration to MySQL
ADMIN_DB_URL=mysql+pymysql://user:pass@host:3306/assistantai_admin
```

**Important**: The file is automatically updated - no manual editing needed!

## Rollback Procedure

If something goes wrong:

1. **Restore from backup** (if available)
2. **Edit `.env`** back to previous `ADMIN_DB_URL`
3. **Restart the application**
4. Contact support with error details

## Docker Deployment

For Docker deployments:

1. Ensure database container is running:
   ```bash
   docker-compose up -d postgres  # or mysql
   ```

2. Get container network details:
   ```bash
   docker network inspect <network_name>
   ```

3. Use container name as host in migration settings:
   ```
   Host: postgres (or mysql service name)
   Port: 5432 (or 3306)
   ```

4. After migration, restart containers:
   ```bash
   docker-compose restart app
   ```

## API Endpoints (For Developers)

### Get Admin DB Info
```
GET /api/settings/admin-db/info
```

Response:
```json
{
  "admin_db": {
    "type": "sqlite",
    "accessible": true,
    "table_count": 15,
    "size_bytes": 524288
  }
}
```

### Test Connection
```
POST /api/settings/admin-db/test
Body: {
  "db_type": "postgresql",
  "host": "localhost",
  "port": 5432,
  "username": "user",
  "password": "pass",
  "database": "db_name"
}
```

### Create Database
```
POST /api/settings/admin-db/create
Body: {
  "db_type": "postgresql",
  "host": "localhost",
  "port": 5432,
  "username": "user",
  "password": "pass",
  "database": "db_name"
}
```

### Migrate Admin Database
```
POST /api/settings/admin-db/migrate
Body: {
  "db_type": "postgresql",
  "host": "localhost",
  "port": 5432,
  "username": "user",
  "password": "pass",
  "database": "db_name"
}
```

## Best Practices

1. **Test First**: Always test connection before migrating
2. **Timing**: Migrate during off-hours to minimize disruption
3. **Backup**: Create manual backups before migration
4. **Documentation**: Document your new database location
5. **Monitoring**: Monitor the new database after migration
6. **Restart**: Always restart the app after migration
7. **Verify**: Check that all data is present after restart

## Common Migration Scenarios

### Scenario 1: Local Development to Production PostgreSQL
```
Source: sqlite:///assistantai.db (local)
Target: postgresql://prod_user:secret@db.prod.example.com:5432/assistantai_prod
```

### Scenario 2: Small SQLite to Local PostgreSQL
```
Source: sqlite:///assistantai.db
Target: postgresql://app_user:app_pass@localhost:5432/assistantai_local
```

### Scenario 3: SQLite to AWS RDS PostgreSQL
```
Source: sqlite:///assistantai.db
Target: postgresql://app_user:app_pass@assistantai-prod.abc123.us-east-1.rds.amazonaws.com:5432/assistantai
```

## Support

For issues or questions:
1. Check this guide first
2. Review the error message in Settings
3. Check application logs
4. Contact your administrator or support team

---

**Last Updated**: 2026-06-14
**Version**: 1.0
**Status**: Production Ready
