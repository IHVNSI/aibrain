# How to Configure the App

Welcome to the **Assistant AI Configuration Guide**! This comprehensive guide covers all the settings and configuration options available in the application. Whether you're a system administrator or an advanced user, this guide will walk you through each setting tab and explain how to optimize your setup.

## Table of Contents

1. [Overview](#overview)
2. [LLM Configuration](#llm-configuration)
3. [Source Database Configuration](#source-database-configuration)
4. [Admin Database Configuration](#admin-database-configuration)
5. [SQLite DBMS (Admin DB Inspector)](#sqlite-dbms-admin-db-inspector)
6. [Vector Database Configuration](#vector-database-configuration)
7. [Training & RAG (Knowledge Base)](#training--rag-knowledge-base)
8. [Data Exchange](#data-exchange)
9. [Documentation](#documentation)
10. [Authentication Configuration](#authentication-configuration)
11. [Security Settings](#security-settings)
12. [Audio Settings](#audio-settings)
13. [Conversations Management](#conversations-management)
14. [Audit Logs](#audit-logs)
15. [Caching & Metrics](#caching--metrics)
16. [Best Practices](#best-practices)

---

## Overview

The Settings panel is your central hub for configuring all aspects of the Assistant AI application. Access it by clicking the **Settings icon (⚙️)** in the top navigation bar.

### Available Configuration Tabs

| Tab | Purpose | Complexity |
|-----|---------|-----------|
| **LLM Config** | Language model provider and model selection | Medium |
| **Source DB** | Business data database connection | Medium |
| **Admin DB** | Application database and migration | High |
| **SQLite DBMS** | Admin database inspection and editing | Advanced |
| **Vector DB** | Knowledge base vector store configuration | Medium |
| **Training / RAG** | Knowledge base file uploads and management | Medium |
| **Data Exchange** | Import/export data and backup management | Medium |
| **DOCS** | View integrated documentation | Basic |
| **Authentication** | User authentication and authorization setup | High |
| **Security** | Security policies and access control | High |
| **Audio** | Voice input and text-to-speech settings | Basic |
| **Conversations** | Manage conversation history and search | Basic |
| **Audit Logs** | View system activity and user actions | Advanced |
| **Caching / Metrics** | Performance monitoring and caching | Advanced |

---

## LLM Configuration

### Purpose
Configure which Language Model (LLM) provider and model the application uses for understanding and responding to queries.

### What is an LLM?
A Large Language Model (LLM) is an AI that understands natural language and generates responses. The app uses it to:
- Understand your queries in plain English
- Generate SQL from your questions
- Extract information from your data
- Provide intelligent responses

### Accessing LLM Config

1. Click **Settings** (⚙️)
2. Click the **LLM Config** tab

### Configuration Steps

#### Step 1: Choose Your Provider

Select from these options:

**1. Google Gemini** (Recommended for most users)
- ✅ Free tier available (2 million tokens/minute)
- ✅ Excellent performance
- ✅ No credit card required for free tier
- 📝 Requires API key from Google AI Studio

**2. OpenAI**
- ✅ Industry-leading model (GPT-4o)
- ✅ Highly reliable
- ⚠️ Requires paid API key
- 💰 ~$0.01 per 1K tokens

**3. Anthropic Claude**
- ✅ Strong reasoning capabilities
- ✅ Excellent for complex queries
- ⚠️ Requires paid API key
- 💰 Competitive pricing

**4. Hugging Face (Offline)**
- ✅ Runs locally on your machine
- ✅ Completely free
- ✅ No internet required
- ⚠️ Slower than cloud providers
- ⚠️ Requires more system resources

#### Step 2: Select a Model

Once you choose a provider, select from available models:

**Google Gemini:**
- `gemini-2.0-flash` (Recommended - Latest and fastest)
- `gemini-1.5-pro` (More powerful, slightly slower)

**OpenAI:**
- `gpt-4o-mini` (Fastest, most economical)
- `gpt-4o` (Recommended - Good balance)
- `gpt-4-turbo` (Most capable)

**Anthropic Claude:**
- `claude-sonnet-4-6` (Fastest)
- `claude-3-5-sonnet-20241022` (Most capable)

**Hugging Face:**
- `google/flan-t5-base` (Faster, requires less memory)
- `google/flan-t5-large` (Better quality, more resource intensive)

#### Step 3: Enter API Key (if applicable)

For cloud providers, enter your API key:

**How to get API keys:**

1. **Google Gemini:**
   - Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
   - Click "Get API Key"
   - Create a new API key
   - Copy and paste into the field

2. **OpenAI:**
   - Visit [OpenAI API Keys](https://platform.openai.com/api-keys)
   - Log in or create account
   - Create new secret key
   - Copy and paste into the field
   - Add billing method

3. **Anthropic:**
   - Visit [Anthropic Console](https://console.anthropic.com/account/keys)
   - Click "Create Key"
   - Copy and paste into the field
   - Add billing method

#### Step 4: Adjust Temperature (Optional)

**Temperature** controls randomness in responses:
- **0.0** - Deterministic, exact same response every time (best for data queries)
- **0.5** - Balanced (default, good for most use cases)
- **1.0** - Most creative/random (good for brainstorming)

**Recommendation:** Keep at default (0) for consistent database query results.

#### Step 5: Save Settings

Click **Save** button. You'll see:
- ✅ Success message if settings are valid
- ⚠️ Error message if API key is invalid or connection fails

### Testing Your Configuration

After saving, check the **Engine Status** badge at the top of Settings:
- 🟢 **Green "Engine ready"** - LLM is working properly
- 🔴 **Gray "Engine not ready"** - Check your configuration

### Troubleshooting

| Problem | Solution |
|---------|----------|
| "Invalid API Key" | Verify key is correct, hasn't expired, and has proper permissions |
| "Connection timeout" | Check internet connection, API endpoint availability |
| "Rate limit exceeded" | You've exceeded API usage limits. Upgrade plan or wait. |
| "Model not found" | Selected model may not be available in your region |
| Offline mode not working | Ensure you have enough disk space and RAM for Hugging Face models |

---

## Source Database Configuration

### Purpose
Connect to your business data source (PostgreSQL, MySQL, SQLite, MongoDB, etc.) so the app can generate and execute SQL queries against your data.

### Key Points
- This is where your **actual business data** lives
- Different from Admin DB (which stores app settings and conversations)
- Queries run against this database are never modified or stored

### Accessing Source DB Config

1. Click **Settings** (⚙️)
2. Click the **Source DB** tab

### Configuration Options

#### Two Input Modes

**Mode 1: Connection String (Advanced)**
- Paste full SQLAlchemy connection string
- For users who prefer raw URLs

**Mode 2: Form Builder (Recommended)**
- Interactive form with fields
- Easy for most users
- Automatic URL generation

### Supported Database Types

| Database | Driver | Port | Connection String Format |
|----------|--------|------|---------------------------|
| PostgreSQL | psycopg2 | 5432 | `postgresql+psycopg2://user:pass@host:5432/db` |
| MySQL | pymysql | 3306 | `mysql+pymysql://user:pass@host:3306/db` |
| SQLite | - | - | `sqlite:///path/to/database.db` |
| MongoDB | - | 27017 | `mongodb://user:pass@host:27017/db` |
| SQL Server | pyodbc | 1433 | `mssql+pyodbc://user:pass@host/db?driver=ODBC+Driver+17` |

### Configuration Steps (Form Mode)

1. **Select Database Type**
   - Choose from: PostgreSQL, MySQL, SQLite, MongoDB, SQL Server

2. **Enter Connection Details**
   - **Host/Server** - Hostname or IP address
   - **Port** - Database port (auto-filled based on type)
   - **Username** - Database user account
   - **Password** - Database password
   - **Database Name** - Database or schema name

3. **Optional Connection Options**
   - Add parameters like `?ssl=true` for PostgreSQL
   - Format: `key=value&key2=value2`

4. **Preview Connection String**
   - See the generated URL in a blue box
   - Verify it looks correct

5. **Test Connection**
   - Click **Test** button
   - Should see "Connection OK" message

6. **Save Settings**
   - Click **Save** to apply

### Important Security Notes

⚠️ **Password Handling:**
- Passwords are masked in the UI (shown as `••••••••`)
- Stored encrypted on the server
- Never echoed back to client

⚠️ **Connection Best Practices:**
- Use read-only database user if possible
- Never use admin/root credentials
- Use strong passwords (20+ characters)
- Enable SSL/TLS for remote connections

### Examples

**PostgreSQL (Local Development)**
```
Host: localhost
Port: 5432
Username: app_user
Password: app_password
Database: sales_db
```

**MySQL (AWS RDS)**
```
Host: mysql-prod.abc123.us-east-1.rds.amazonaws.com
Port: 3306
Username: admin
Password: SecurePass123
Database: production_db
```

**SQLite (Local File)**
```
Host: (N/A)
Port: (N/A)
Database: /data/local_database.db
```

### Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "Connection refused" | Database not running | Start your database server |
| "Authentication failed" | Wrong credentials | Verify username and password |
| "Database not found" | Database doesn't exist | Create the database first |
| "Port already in use" | Wrong port number | Verify correct database port |
| "SSL certificate error" | SSL configuration issue | Add `?ssl=false` or configure SSL |

---

## Admin Database Configuration

### Purpose
Migrate the application's internal database (Admin DB) from SQLite to PostgreSQL or MySQL for better scalability and production deployments.

The Admin DB stores:
- 💬 All conversations and chat history
- ⚙️ Application settings (LLM config, audio settings)
- 📚 Training data and knowledge base metadata
- 📊 Audit logs and user activity
- 🔐 Authentication data

### When to Migrate

**Stay with SQLite if:**
- Single user or small team
- Development/testing environment
- Minimal concurrent connections

**Migrate to PostgreSQL/MySQL if:**
- Multiple concurrent users
- Production deployment
- Need advanced backup/recovery
- Want horizontal scaling

### Accessing Admin DB Config

1. Click **Settings** (⚙️)
2. Click the **Admin DB** tab

### Key Features

**Information Mode:**
- View current database type and status
- See table count and file size
- Understand migration benefits

**Migrate Mode:**
- Step-by-step migration wizard
- Test connection before migrating
- Create target database automatically
- Migrate all data with one click

### Migration Process

See [Database Migration Guide](Database_Migration_Guide.md) for comprehensive instructions.

### Quick Steps

1. Go to Admin DB tab → **Migrate** mode
2. Select target database type
3. Enter connection details
4. Click **Test Connection**
5. Click **Create DB** (optional - auto-creates)
6. Click **Migrate Data**
7. **Restart the application**
8. Verify data in new database

---

## SQLite DBMS (Admin DB Inspector)

### Purpose
Inspect and manually edit the Admin Database tables. Useful for:
- Database troubleshooting
- Fixing corrupted records
- Advanced administration
- Data verification

### ⚠️ WARNING
Only use this if you understand SQL and databases. Incorrect edits can corrupt data!

### Accessing SQLite Inspector

1. Click **Settings** (⚙️)
2. Click the **SQLite DBMS** tab
3. Only available if Admin DB is SQLite

### Features

#### View Tables
- Lists all database tables
- Shows row count for each
- Displays column information
- Identifies primary keys

#### Browse Data
- View table contents with pagination
- 30 rows per page (adjustable)
- Filter and search capability
- See column types and constraints

#### Edit Records
- **Add rows** - Insert new records
- **Update rows** - Modify existing data
- **Delete rows** - Remove records
- All changes immediately saved

#### Column Information
For each table, see:
- Column name
- Data type (TEXT, INTEGER, etc.)
- Nullable status
- Default values
- Primary key designation

### Important Tables

| Table | Purpose |
|-------|---------|
| `users` | User accounts and authentication |
| `conversations` | Chat conversations and metadata |
| `messages` | Individual chat messages |
| `settings` | Application configuration |
| `training_items` | Knowledge base documents |
| `audit_logs` | System activity logs |
| `user_settings` | User preferences (audio, etc.) |

### Editing Best Practices

✅ **Do:**
- Backup database before editing
- Make small, targeted changes
- Test changes in development first
- Document what you changed

❌ **Don't:**
- Modify system tables without understanding
- Delete rows without verification
- Edit foreign keys without checking references
- Change data types without understanding implications

---

## Vector Database Configuration

### Purpose
Configure where the knowledge base embeddings are stored. Vector databases store semantic representations of your documents, enabling intelligent search and retrieval.

### What is a Vector Database?
Converts your documents into mathematical vectors, allowing the system to:
- Find semantically similar documents
- Understand document meaning
- Provide intelligent search results
- Enable RAG (Retrieval-Augmented Generation)

### Accessing Vector DB Config

1. Click **Settings** (⚙️)
2. Click the **Vector DB** tab

### Available Options

#### 1. ChromaDB (Recommended for Development)
- ✅ Default option
- ✅ Stores data locally
- ✅ No external service needed
- ✅ Easy setup
- ❌ Not ideal for production
- **Configuration:** Just specify local path

```
Default Path: ./vanna_chroma
```

#### 2. FAISS (Recommended for Production)
- ✅ Fast similarity search
- ✅ Works locally or distributed
- ✅ Excellent performance
- ✅ Facebook's proven technology
- **Configuration:** Specify storage path

```
Path: ./vanna_faiss
```

#### 3. Pinecone (Cloud-Based)
- ✅ Fully managed service
- ✅ Scales automatically
- ✅ Enterprise-grade
- ⚠️ Requires API key
- ⚠️ Monthly cost
- **Configuration:** API key + index name

### Configuration Steps

1. **Select Vector Store**
   - Choose from available options

2. **For Pinecone (if selected):**
   - Get API key from [Pinecone Console](https://app.pinecone.io)
   - Enter Pinecone API key
   - Enter index name
   - Enter environment (e.g., "us-east-1-aws")

3. **For ChromaDB or FAISS:**
   - Verify storage path exists
   - Ensure sufficient disk space
   - Path can be relative or absolute

4. **Save Settings**
   - Click **Save**
   - System will initialize vector store

### Storage Requirements

| Store | Storage | Embedding Size | Query Speed |
|-------|---------|----------------|-------------|
| ChromaDB | 1-10GB | ~1500 vectors = 6MB | 100-500ms |
| FAISS | 1-100GB | Scalable | 50-200ms |
| Pinecone | Unlimited | Scalable | 50-100ms |

### Troubleshooting

| Issue | Solution |
|-------|----------|
| "Storage path not writable" | Check file permissions, disk space |
| "Pinecone connection failed" | Verify API key, network connection |
| "Out of memory" | Vector store too large, reduce documents |
| "Embedding failed" | Restart application, check logs |

---

## Training & RAG (Knowledge Base)

### Purpose
Upload documents for the AI to reference when answering questions. This enables Retrieval-Augmented Generation (RAG) - combining AI with your actual documents.

### What Can You Upload?

- 📄 **PDF** - Documents, reports, manuals
- 📝 **Word** (.docx) - Detailed documentation
- 📊 **Excel** (.xlsx) - Data tables, specifications
- 🎯 **PowerPoint** (.pptx) - Presentations, training materials
- 🖼️ **Images** (.png, .jpg) - Diagrams, screenshots

### Accessing Training Tab

1. Click **Settings** (⚙️)
2. Click the **Training / RAG** tab

### Features

#### Upload Documents
1. Click **Upload** button
2. Select files from your computer
3. Can upload multiple files at once
4. System processes and indexes them

#### View Training Items
- See all uploaded documents
- View upload date
- See processing status
- Access and manage items

#### Search Training Data
- Full-text search across all documents
- Filter by document type
- Sort by date, size, relevance

#### Delete Training Items
- Remove documents no longer needed
- Frees up vector storage space
- Remove outdated information

#### Access Control
Some documents may be marked:
- `[ACCESS:AUTHENTICATED]` - Only logged-in users can see
- `[ACCESS:ADMIN]` - Only admins can see

### Training Workflow

1. **Upload Documents**
   - Click Upload button
   - Select your files (multiple at once OK)
   - Wait for processing

2. **System Processing**
   - Extracts text from documents
   - Creates semantic embeddings
   - Stores in vector database
   - Indexes for search

3. **Use in Queries**
   - When you ask questions, AI searches docs
   - Relevant sections automatically included
   - Better, more informed answers

4. **Monitor Usage**
   - View processing status
   - See which docs are being used
   - Track storage usage

### Best Practices

✅ **Do:**
- Use clear document names
- Organize by topic/department
- Update outdated documents
- Include table of contents in PDFs
- Use high-quality scanned documents

❌ **Don't:**
- Upload personal/sensitive data
- Upload extremely large documents (1GB+)
- Upload corrupted or locked files
- Store duplicate information

### File Size Limits

| Type | Max Size | Notes |
|------|----------|-------|
| PDF | 50MB | OCR-enabled for scanned docs |
| Word | 30MB | Includes all formatting |
| Excel | 20MB | All sheets processed |
| PowerPoint | 30MB | Text and speaker notes |
| Image | 10MB | Text extraction via OCR |

---

## Data Exchange

### Purpose
Import/export data, backup settings, and manage bulk data operations.

### Accessing Data Exchange

1. Click **Settings** (⚙️)
2. Click the **Data Exchange** tab

### Features

#### Export Data
- **Export Conversations** - Download all chat history as JSON/CSV
- **Export Settings** - Backup your configuration
- **Export Training Data** - Backup knowledge base metadata

#### Import Data
- **Import Conversations** - Restore from backup
- **Import Training Data** - Batch upload documents
- **Restore Settings** - Apply previous configuration

#### Backup Operations
- Full application backup (all data)
- Selective backups (specific tables)
- Scheduled backups
- Backup scheduling

#### Data Formats
- **JSON** - For data preservation, interchange
- **CSV** - For spreadsheet compatibility
- **SQL** - For database restoration

### How to Backup

1. Click **Export All**
2. Choose format (JSON recommended)
3. Save file to secure location
4. Store backup date for reference

### How to Restore

1. Click **Import Data**
2. Select file to restore
3. Choose import mode:
   - **Merge** - Add to existing data
   - **Replace** - Overwrite existing data
   - **Verify** - Check compatibility

4. Review preview of data
5. Confirm import

### Troubleshooting

| Issue | Solution |
|-------|----------|
| "File too large" | Split into smaller exports |
| "Invalid format" | Ensure file is valid JSON/CSV |
| "Import failed" | Check data compatibility |
| "Backup incomplete" | Retry, check disk space |

---

## Documentation

### Purpose
View integrated documentation and guides directly in the app.

### Accessing Docs

1. Click **Settings** (⚙️)
2. Click the **DOCS** tab

### Available Guides

1. **How to Use the App** - User guide for all features
2. **API Usage** - Developer API documentation
3. **Code Structure & Architecture** - Technical architecture
4. **How to Configure the App** - This guide!
5. **Database Migration Guide** - Admin database migration

### Features

- 🔍 **Search** - Search across all documentation
- 📖 **Formatted Display** - Beautiful markdown rendering
- 📥 **Download as PDF** - Get professional PDFs
- 🔗 **Quick Links** - Jump to sections

### Downloading Documentation

1. Select a documentation section
2. Click **PDF** button
3. Professional PDF downloads to your computer
4. Perfect for printing or sharing

---

## Authentication Configuration

### Purpose
Set up authentication methods, configure user roles, and manage access control.

### ⚠️ Important
This is an advanced feature. Incorrect configuration can lock users out or create security holes.

### Accessing Authentication Config

1. Click **Settings** (⚙️)
2. Click the **Authentication** tab

### Authentication Methods

#### 1. Local Authentication
- Username and password stored in app
- Default method
- Good for single organization

#### 2. OAuth 2.0
- External providers (Google, GitHub, etc.)
- Federated authentication
- Single Sign-On (SSO)

#### 3. LDAP/Active Directory
- Enterprise directory integration
- Corporate user management
- Automated provisioning

### User Roles

| Role | Permissions | Use Case |
|------|-----------|----------|
| **Admin** | Full system access, configuration | System administrators |
| **Editor** | Create/edit conversations, upload docs | Regular users |
| **Viewer** | Read-only access | Reports, viewing |
| **Guest** | Limited demo access | Trial users |

### Configuration Steps

1. **Select Authentication Method**
2. **Configure Provider**
   - Enter provider credentials
   - Set redirect URLs
   - Configure scopes/permissions

3. **Set User Roles**
   - Assign default role for new users
   - Specify role mappings
   - Configure role privileges

4. **Enable/Disable Methods**
   - Toggle authentication options
   - Enforce password policies
   - Set session timeouts

### Security Configuration

- **Session Timeout** - 30 minutes (default)
- **Password Policy** - Minimum 12 characters
- **Multi-Factor Authentication** - Optional 2FA
- **IP Whitelisting** - Restrict by IP range

---

## Security Settings

### Purpose
Configure security policies, data encryption, and access control.

### Accessing Security Settings

1. Click **Settings** (⚙️)
2. Click the **Security** tab

### Security Features

#### 1. Data Encryption
- **In Transit** - SSL/TLS for all connections
- **At Rest** - Optional database encryption
- **API Keys** - Never logged or exposed

#### 2. Access Control
- **Role-Based Access Control (RBAC)** - Users get permissions based on role
- **Resource-Level Permissions** - Fine-grained access
- **API Rate Limiting** - Prevent abuse

#### 3. Audit & Compliance
- **Audit Logging** - All actions tracked
- **Compliance Reports** - GDPR, SOC2
- **Data Retention Policies** - Auto-deletion rules

#### 4. Security Policies
- **Password Requirements** - Complexity rules
- **Session Management** - Auto-logout
- **Device Trust** - Device fingerprinting
- **Threat Detection** - Anomaly detection

### Configuration Recommendations

✅ **Recommended Settings:**
- Enable HTTPS/SSL
- Enforce strong passwords
- Enable audit logging
- Set 30-minute session timeout
- Enable rate limiting
- Configure IP whitelist

### Compliance Standards

- ✅ GDPR - Data privacy
- ✅ SOC 2 - Security controls
- ✅ HIPAA - Healthcare data
- ✅ PCI-DSS - Payment data
- ✅ CCPA - California privacy

---

## Audio Settings

### Purpose
Configure voice input (microphone) and audio output (text-to-speech) settings.

### Accessing Audio Settings

1. Click **Settings** (⚙️)
2. Click the **Audio** tab

### Configuration Options

#### Voice Input (Microphone)

| Setting | Range | Default | Effect |
|---------|-------|---------|--------|
| **Microphone Sensitivity** | 0.1 - 1.0 | 0.5 | How sensitive to background noise |

**Adjustment Guide:**
- **0.1** - Very sensitive (picks up all noise)
- **0.5** - Balanced (recommended)
- **1.0** - Only loud speech detected

#### Voice Output (Text-to-Speech)

| Setting | Range | Default | Effect |
|---------|-------|---------|--------|
| **Voice Gender** | Male/Female | Female | TTS voice gender |
| **Pitch** | 0.5 - 2.0 | 1.0 | Voice pitch (higher/lower) |
| **Speaking Rate** | 0.5 - 2.0 | 1.0 | Speed of speech |
| **Volume** | 0.0 - 1.0 | 1.0 | Loudness of audio |

#### Auto-Speak Toggle
- **On** - Automatically read responses aloud
- **Off** - Manual speaker icon required

### Testing Audio

1. Click speaker icon to hear sample
2. Adjust settings as needed
3. Listen to new sample
4. Test with actual voice input
5. Settings auto-save

### Troubleshooting Audio

| Problem | Solution |
|---------|----------|
| No microphone input | Check browser permissions, hardware |
| No audio output | Check system volume, speakers connected |
| Choppy audio | Reduce sensitivity, check network |
| Slow transcription | Reduce microphone sensitivity |
| Quiet voice output | Increase volume slider |

### Best Practices

✅ **Do:**
- Use headphones for better quality
- Test in quiet environment
- Adjust sensitivity for your space
- Calibrate pitch and rate for preference

❌ **Don't:**
- Turn off background noise detection
- Set extreme volume levels
- Use very high sensitivity in loud spaces

---

## Conversations Management

### Purpose
Manage conversation history, search conversations, and organize chats.

### Accessing Conversations

1. Click **Settings** (⚙️)
2. Click the **Conversations** tab

### Features

#### View All Conversations
- List all user conversations
- See creation date and last message
- View participant information
- Sort by date, name, relevance

#### Search Conversations
- Full-text search across all messages
- Filter by date range
- Filter by participant
- Find specific queries or responses

#### Manage Conversations
- **Rename** - Change conversation title
- **Archive** - Hide from active list
- **Delete** - Permanently remove
- **Export** - Download conversation as file

#### Bulk Operations
- Select multiple conversations
- Bulk delete old conversations
- Bulk export for backup
- Bulk archive for cleanup

#### Statistics
- Total conversations
- Total messages
- Avg. conversation length
- Storage used

### Searching Tips

**Search Examples:**
- `"sales report"` - Find exact phrase
- `customer AND 2025` - Must contain both
- `NOT confidential` - Exclude term
- `date:2025-01` - Date range
- `from:admin` - From specific user

### Cleanup Best Practices

✅ **Do:**
- Archive old conversations (1+ years)
- Delete test/demo conversations
- Remove personal/sensitive chats
- Export important conversations

❌ **Don't:**
- Delete without backup
- Delete active project conversations
- Delete without searching for references

---

## Audit Logs

### Purpose
View system activity and user actions for security, compliance, and troubleshooting.

### Accessing Audit Logs

1. Click **Settings** (⚙️)
2. Click the **Audit Logs** tab

### What's Logged

| Action | Logged Details |
|--------|-----------------|
| **User Login** | Username, IP, timestamp, browser |
| **Configuration Changes** | What changed, old/new values, user, timestamp |
| **Data Access** | What data accessed, user, time, IP |
| **File Upload** | File name, size, user, timestamp |
| **Security Events** | Failed logins, permission denials, suspicious activity |
| **System Events** | Backups, migrations, restarts, errors |

### Log Format

Each log entry shows:
- **Timestamp** - When it happened
- **User** - Who did it
- **Action** - What happened
- **Resource** - What was affected
- **IP Address** - Where from
- **Status** - Success/failure
- **Details** - Additional context

### Filtering Logs

Filter by:
- **Date Range** - Custom start/end dates
- **User** - Specific user
- **Action Type** - Login, config change, etc.
- **Status** - Success, failure
- **IP Address** - Specific address

### Exporting Logs

1. Apply filters
2. Click **Export**
3. Choose format:
   - CSV (for spreadsheets)
   - JSON (for systems)
   - PDF (for reports)

### Compliance Reports

- **SOC 2 Report** - Last 30 days activity
- **GDPR Export** - User data and consent
- **Audit Trail** - Complete activity log
- **Security Report** - Failed logins, anomalies

### Retention Policy

- **Default** - 90 days
- **Extended** - 1 year (enterprise)
- **Custom** - Configure retention period

---

## Caching & Metrics

### Purpose
Monitor performance, view system metrics, and manage caching strategies.

### Accessing Caching & Metrics

1. Click **Settings** (⚙️)
2. Click the **Caching / Metrics** tab

### Performance Metrics

#### Response Times
- **Average response time** - How long responses take
- **Median response time** - Middle value (less affected by outliers)
- **P95 response time** - 95th percentile (worst case common)
- **P99 response time** - 99th percentile (rare worst case)

#### Request Metrics
- **Requests/second** - Current load
- **Failed requests** - Error rate percentage
- **Timeout rate** - % of requests timing out
- **Avg. request size** - Data transfer

#### Cache Performance
- **Cache hit rate** - % of requests served from cache
- **Cache miss rate** - % requiring full processing
- **Cache size** - Current cache storage used
- **Memory usage** - RAM consumed

### Caching Configuration

#### Query Result Caching
- **Enable** - Cache database query results
- **TTL (Time to Live)** - How long cache lasts
- **Max Size** - Maximum cached data

#### API Response Caching
- **Enable** - Cache API responses
- **Duration** - Cache lifetime in minutes
- **Compression** - Reduce cache size

#### Document Embedding Cache
- **Enable** - Cache vector embeddings
- **Size Limit** - Max embeddings to cache
- **Auto-refresh** - Update old cache

### Performance Optimization

#### Clear Cache
- Clear all cached data
- Free up memory
- Start fresh

#### View Cache Stats
- Cache efficiency
- Most cached queries
- Cache memory breakdown

#### Monitor Resource Usage
- CPU usage
- Memory usage
- Disk I/O
- Network usage

### Alerts & Thresholds

Set alerts for:
- **Response time > X ms** - Slow performance
- **Error rate > X%** - Too many failures
- **Memory usage > X%** - Running low on RAM
- **Cache hit rate < X%** - Poor cache efficiency

### Optimization Recommendations

✅ **Enable caching if:**
- Running many repeated queries
- Have sufficient memory available
- Want faster response times

✅ **Disable caching if:**
- Data changes very frequently
- Memory is limited
- Need real-time data always

### Troubleshooting Performance

| Issue | Cause | Solution |
|-------|-------|----------|
| Slow responses | Cache hits low | Increase cache size |
| High memory | Cache too large | Reduce cache TTL |
| Stale data | Cache not refreshing | Lower cache TTL |
| Failed requests | Database slow | Check Source DB |

---

## Best Practices

### Configuration Checklist

#### Security ✅
- [ ] Set strong admin password
- [ ] Enable SSL/TLS
- [ ] Configure authentication
- [ ] Enable audit logging
- [ ] Set up firewall rules

#### Performance ✅
- [ ] Configure appropriate LLM
- [ ] Enable query caching
- [ ] Monitor metrics
- [ ] Set up alerts
- [ ] Optimize database indexing

#### Data Management ✅
- [ ] Connect source database
- [ ] Set up regular backups
- [ ] Configure data retention
- [ ] Enable encryption
- [ ] Document connection strings

#### Knowledge Base ✅
- [ ] Configure vector store
- [ ] Upload relevant documents
- [ ] Test retrieval
- [ ] Update documents regularly
- [ ] Monitor vector store size

#### User Management ✅
- [ ] Set up authentication
- [ ] Configure roles
- [ ] Assign users appropriately
- [ ] Enable MFA for admins
- [ ] Review access regularly

### Configuration Best Practices

1. **Document Everything**
   - Keep notes of all changes
   - Document credentials securely
   - Maintain configuration backups
   - Record decisions and reasons

2. **Test Before Production**
   - Test all configurations in dev
   - Verify backups work
   - Test recovery procedures
   - Load test before production

3. **Regular Reviews**
   - Review audit logs weekly
   - Check metrics monthly
   - Update documentation quarterly
   - Review security annually

4. **Backup Strategy**
   - Daily automated backups
   - Weekly full backups
   - Monthly off-site backups
   - Test restore monthly

5. **Monitoring**
   - Set up performance alerts
   - Monitor error rates
   - Watch for security anomalies
   - Track resource usage

### Troubleshooting Workflow

1. **Identify Problem**
   - Check error messages
   - Review audit logs
   - Check metrics
   - Test connectivity

2. **Isolate Issue**
   - Is it LLM related?
   - Is it database related?
   - Is it configuration?
   - Is it user error?

3. **Gather Information**
   - Collect logs
   - Note timestamps
   - Document steps to reproduce
   - Take screenshots

4. **Apply Fix**
   - Start with simplest solution
   - Make one change at a time
   - Test thoroughly
   - Document what worked

5. **Verify Solution**
   - Test multiple times
   - Monitor for issues
   - Update documentation
   - Notify users if needed

---

## Next Steps

1. **Complete Initial Setup**
   - Configure LLM provider
   - Connect source database
   - Set up authentication
   - Configure audio settings

2. **Test All Features**
   - Run test queries
   - Upload sample documents
   - Test voice input
   - Verify backups

3. **Optimize Performance**
   - Monitor initial metrics
   - Adjust caching settings
   - Review database performance
   - Configure alerts

4. **Secure Your System**
   - Enable all security features
   - Set up audit logging
   - Configure backups
   - Review access control

5. **Train Users**
   - Share "How to Use" guide
   - Conduct training sessions
   - Document workflows
   - Provide support resources

---

## Support & Resources

- 📖 **User Guide** - See "How to Use the App"
- 🔌 **API Documentation** - See "API Usage" in DOCS tab
- 🏗️ **Architecture Guide** - See "Code Structure & Architecture"
- 🗄️ **Database Guide** - See "Database Migration Guide"
- 💬 **Chat Support** - Contact your administrator

---

**Last Updated:** 2026-06-14  
**Version:** 1.0  
**Status:** Production Ready
