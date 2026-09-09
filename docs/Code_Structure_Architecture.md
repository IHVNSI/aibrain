# Code Structure, Architecture & Component Relationships

Welcome to the **Developer Guide**! This comprehensive documentation covers the codebase architecture, technology stack, component relationships, and how everything works together. Perfect for co-developers looking to understand and contribute to the Assistant AI project.

## Table of Contents

1. [Technology Stack](#technology-stack)
2. [Project Structure](#project-structure)
3. [Architecture Overview](#architecture-overview)
4. [Frontend Architecture](#frontend-architecture)
5. [Backend Architecture](#backend-architecture)
6. [Database Models](#database-models)
7. [API Architecture](#api-architecture)
8. [Component Relationships](#component-relationships)
9. [Data Flow](#data-flow)
10. [Development Setup](#development-setup)
11. [Coding Standards](#coding-standards)
12. [Deployment](#deployment)

---

## Technology Stack

### Frontend Stack

| Technology | Version | Purpose |
|-----------|---------|---------|
| **React** | ^18.3.1 | UI framework |
| **Vite** | ^5.4.8 | Build tool and dev server |
| **Tailwind CSS** | ^3.4.13 | Styling and utility classes |
| **React Router** | ^6.26.2 | Client-side routing |
| **Axios** | ^1.7.7 | HTTP client |
| **React Markdown** | ^10.1.0 | Markdown rendering |
| **Remark GFM** | ^4.0.1 | GitHub-flavored markdown |
| **Recharts** | ^2.15.4 | Data visualization |
| **Lucide React** | ^0.451.0 | Icon library |
| **SweetAlert2** | ^11.26.25 | Modal dialogs |
| **html2canvas** | ^1.4.1 | Content to image conversion |
| **jsPDF** | ^2.5.1 | PDF generation |

### Backend Stack

| Technology | Version | Purpose |
|-----------|---------|---------|
| **Flask** | ^3.0 | Web framework |
| **SQLAlchemy** | ^2.0+ | ORM |
| **Vanna** | ^0.7.5+ | Text-to-SQL engine |
| **ChromaDB** | Latest | Vector database (default) |
| **python-dotenv** | Latest | Environment configuration |
| **Werkzeug** | Latest | Password hashing |
| **PyJWT** | Latest | JWT token handling |
| **python-docx** | Latest | Word document processing |
| **openpyxl** | Latest | Excel file processing |
| **python-pptx** | Latest | PowerPoint processing |
| **pypdf** | Latest | PDF text extraction |
| **Pillow** | Latest | Image processing |

### Database Options

| Type | Default | Purpose |
|------|---------|---------|
| **Admin DB** | SQLite | Conversations, settings, training metadata |
| **Source DB** | PostgreSQL/MySQL/SQLite | Business data to query |
| **Vector Store** | ChromaDB | Knowledge base embeddings (alternatives: FAISS, Pinecone) |

---

## Project Structure

```
assistantai/
├── backend/                          # Flask backend application
│   ├── app/
│   │   ├── __init__.py              # Flask app initialization, DB setup
│   │   ├── analysis.py              # Data analysis utilities
│   │   ├── auth.py                  # Authentication logic
│   │   ├── bootstrap.py             # Initial data seeding
│   │   ├── config.py                # Configuration management
│   │   ├── extensions.py            # Flask extensions (SQLAlchemy, JWT)
│   │   ├── microservice_auth.py     # Microservice token validation
│   │   ├── models.py                # SQLAlchemy ORM models
│   │   ├── responder.py             # AI response generation
│   │   ├── response_guide.py        # Response formatting
│   │   ├── sql_guard.py             # SQL security filtering
│   │   ├── user_filter.py           # Row-level access control
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py              # Auth endpoints (login, register)
│   │   │   ├── auth_config.py       # Auth provider configuration
│   │   │   ├── cache.py             # Caching endpoints
│   │   │   ├── chat.py              # Main chat endpoint
│   │   │   ├── conversations.py     # Conversation management
│   │   │   ├── data_exchange.py     # Data import/export
│   │   │   ├── security.py          # Security settings
│   │   │   ├── settings.py          # Application settings
│   │   │   ├── training.py          # Training data endpoints
│   │   │   └── __init__.py
│   │   ├── conversation/
│   │   │   ├── __init__.py
│   │   │   └── manager.py           # Conversation persistence logic
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   ├── factory.py           # LLM provider factory
│   │   │   └── providers.py         # LLM provider implementations
│   │   └── vanna_service/
│   │       ├── __init__.py
│   │       └── service.py           # Vanna text-to-SQL service
│   ├── run.py                       # Application entry point
│   ├── requirements.txt             # Python dependencies
│   ├── check_user.py               # User validation script
│   ├── check_source_user.py        # Source DB user checker
│   ├── generate_token.py           # JWT token generator
│   ├── reset_admin.py              # Reset admin credentials
│   ├── sync_user.py                # User synchronization
│   ├── .env                         # Environment variables
│   ├── assistantai.db              # SQLite admin database
│   ├── vanna_chroma/               # ChromaDB vector store
│   └── instance/
│
├── frontend/                         # React frontend application
│   ├── src/
│   │   ├── main.jsx                # Entry point
│   │   ├── index.css               # Global styles
│   │   ├── App.jsx                 # Root component
│   │   ├── api/
│   │   │   └── client.js           # Axios API client
│   │   ├── contexts/
│   │   │   └── AuthContext.jsx     # Authentication context
│   │   ├── components/
│   │   │   ├── AuthConfigPanel.jsx # Authentication UI
│   │   │   └── ChartRenderer.jsx   # Chart visualization
│   │   ├── pages/
│   │   │   ├── Login.jsx           # Login page
│   │   │   ├── Chat.jsx            # Main chat interface
│   │   │   └── Settings.jsx        # Settings dashboard
│   │   └── utils/
│   │       └── formatters.js       # Utility functions
│   ├── package.json                # Node.js dependencies
│   ├── vite.config.js              # Vite configuration
│   ├── tailwind.config.js          # Tailwind CSS config
│   ├── postcss.config.js           # PostCSS config
│   └── index.html                  # HTML entry point
│
├── docs/                            # Documentation
│   ├── How_to_Use_the_App.md
│   ├── API_Usage.md
│   └── Code_Structure_Architecture.md
│
├── README.md                        # Project overview
└── .gitignore                       # Git ignore rules
```

---

## Architecture Overview

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        WEB BROWSER                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │             React Frontend (Vite)                        │  │
│  │  - Login/Auth                                            │  │
│  │  - Chat Interface                                        │  │
│  │  - Settings Dashboard                                   │  │
│  │  - Voice Input/Output                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                           │ HTTP/HTTPS
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FLASK BACKEND (Port 5001)                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │               API Routes & Endpoints                     │  │
│  │  - /api/auth/*          (Authentication)                │  │
│  │  - /api/chat            (Query Processing)              │  │
│  │  - /api/training/*      (Training Data)                 │  │
│  │  - /api/conversations/* (History Management)            │  │
│  │  - /api/settings/*      (User Preferences)              │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Business Logic Layer                    │  │
│  │  - Authentication & Authorization                       │  │
│  │  - Conversation Management                              │  │
│  │  - Query Routing (DB/KB/Direct)                         │  │
│  │  - SQL Security Filtering                               │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │               LLM Integration Layer                      │  │
│  │  - Vanna (Text-to-SQL)                                  │  │
│  │  - Provider Abstraction (OpenAI, Gemini, Claude, etc.) │  │
│  │  - Prompt Management                                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  Admin SQLite    │ │  Vector Store    │ │   Source DB      │
│  (Conversations) │ │   (ChromaDB)     │ │ (PostgreSQL/etc) │
│  (Settings)      │ │ (Knowledge Base) │ │  (Business Data) │
│  (Training Meta) │ │  (Embeddings)    │ │                  │
└──────────────────┘ └──────────────────┘ └──────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  LLM APIs        │ │  Embedding Model │ │  External APIs   │
│ (Gemini/OpenAI) │ │  (Sentence Trans) │ │  (if configured) │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

---

## Frontend Architecture

### Component Hierarchy

```
App (Root)
├── AuthContext (Provider)
├── Login (Page)
│   └── Login Form
├── Chat (Page)
│   ├── Sidebar
│   │   ├── Conversation List
│   │   ├── Edit Dialog (inline)
│   │   └── New Chat Button
│   ├── Main Chat Area
│   │   ├── Message List
│   │   │   └── MessageBubble (repeated)
│   │   │       ├── Text Content
│   │   │       ├── SQL Query Display
│   │   │       ├── Data Table
│   │   │       ├── ChartRenderer
│   │   │       └── Action Buttons (Speaker, Copy, Download)
│   │   └── Message Input
│   │       ├── Text Input Box
│   │       ├── Microphone Button (Voice Input)
│   │       ├── Send Button
│   │       └── Voice Transcription Display
│   └── Top Navigation
│       ├── Settings Button
│       ├── User Profile
│       └── Logout Button
└── Settings (Page)
    ├── Tab Navigation (13 tabs)
    ├── LLM Config Tab
    ├── Database Config Tab
    ├── Vector Store Tab
    ├── Training/RAG Tab
    ├── DOCS Tab (API Doc Tab)
    │   ├── Documentation Sidebar
    │   ├── Search Bar
    │   ├── PDF Download Button
    │   └── Markdown Content Display
    ├── Audio Tab
    ├── Security Tab
    ├── Conversations Tab
    ├── Cache/Metrics Tab
    └── Other Admin Tabs
```

### Key Frontend Components

#### 1. **Chat.jsx** (Main Chat Interface)
- **Purpose:** Primary user interaction point
- **State Management:**
  - `conversations` - List of all conversations
  - `currentConvId` - Active conversation ID
  - `messages` - Chat messages in current conversation
  - `input` - Current message input
  - `isListening` - Voice input status
  - `audioSettings` - User audio preferences
  - `editingConvId`, `editingTitle` - Conversation rename state
- **Features:**
  - Real-time voice input with Web Speech API
  - Manual text editing during voice transcription
  - "Clear Text" command detection
  - Audio playback with customizable settings
  - Conversation management (rename, delete)

#### 2. **Login.jsx** (Authentication)
- **Purpose:** User login and guest access
- **Features:**
  - Email/password authentication
  - Guest login (guest@guest.com / Guest123)
  - JWT token handling
  - Redirect on successful login

#### 3. **Settings.jsx** (Configuration Dashboard)
- **Purpose:** Application settings and configuration
- **13 Tabs:**
  - LLM Config - Provider and model selection
  - Database Config - Source database connection
  - Vector Store - Vector database configuration
  - Training/RAG - Training data management
  - DOCS - Documentation viewer with PDF export
  - Audio - Voice settings persistence
  - Security - SQL security policies
  - Authentication - Auth provider config
  - Conversations - Conversation management
  - Cache - Caching metrics
  - And more...

#### 4. **ChartRenderer.jsx** (Data Visualization)
- **Purpose:** Render charts from query results
- **Features:**
  - Recharts for bar, line, pie charts
  - Auto-detection of chart type
  - Interactive legend and tooltips

#### 5. **AuthConfigPanel.jsx** (Auth Configuration)
- **Purpose:** Configure authentication providers
- **Features:**
  - OAuth2/OIDC configuration
  - Provider management

### Frontend State Management

**React Context (AuthContext):**
```javascript
{
  user: { id, email, name, roles },
  token: "JWT_TOKEN",
  isAuthenticated: boolean,
  login: (email, password) => Promise,
  logout: () => void
}
```

**Component Local State:**
- Each page manages its own state (messages, conversations, etc.)
- Audio settings loaded from API on mount

---

## Backend Architecture

### Flask Application Structure

#### 1. **app/__init__.py** (Application Factory)
```python
# Creates Flask app with:
- SQLAlchemy database initialization
- JWT authentication setup
- Blueprint registration
- Migration handling
- CORS configuration
```

#### 2. **app/models.py** (Data Models)

**Key Models:**

| Model | Purpose | Fields |
|-------|---------|--------|
| `User` | Authentication | id, email, password_hash, name, roles |
| `Conversation` | Chat history | id, user_id, title, created_at, messages |
| `Message` | Chat messages | id, conversation_id, role, content, metadata |
| `TrainingItem` | Training data | id, type (ddl/doc/sql/kb), content, access_level, embeddings |
| `UserSettings` | User preferences | id, user_id, audio_settings (JSON), auto_speak |
| `AuditLog` | Security audit | id, user_id, action, resource, timestamp |

#### 3. **app/api/** (API Endpoints)

**auth.py** - Authentication endpoints
```python
POST   /api/auth/login              # Login with credentials
POST   /api/auth/register           # Create new account
POST   /api/auth/refresh            # Refresh JWT token
POST   /api/auth/logout             # Invalidate token
```

**chat.py** - Query processing
```python
POST   /api/chat                    # Submit query (main endpoint)
```

**conversations.py** - Conversation management
```python
GET    /api/conversations           # List conversations
GET    /api/conversations/{id}      # Get specific conversation
PUT    /api/conversations/{id}/rename
DELETE /api/conversations/{id}      # Delete conversation
```

**training.py** - Training data management
```python
POST   /api/training/ddl            # Upload table schemas
POST   /api/training/documentation  # Upload documentation
POST   /api/training/sql-pairs      # Add SQL examples
POST   /api/training/knowledge-base/upload # Upload KB files
```

**settings.py** - User and system settings
```python
GET    /api/settings/user           # Get user settings
POST   /api/settings/user           # Update user settings
GET    /api/settings/engine/status  # Engine status
GET    /api/settings/docs           # List documentation
GET    /api/settings/docs/{slug}    # Get doc content
```

#### 4. **app/conversation/manager.py** (Conversation Persistence)
- **Purpose:** Handle conversation history and context
- **Methods:**
  - `create_conversation()` - Start new conversation
  - `append_turn()` - Add user/AI message pair
  - `get_conversation()` - Retrieve full history
  - `delete_conversation()` - Remove conversation
  - `rename_conversation()` - Update title

#### 5. **app/llm/factory.py** (LLM Provider Factory)
```python
class LLMFactory:
    @staticmethod
    def create(provider_name) -> LLMProvider:
        # Returns appropriate LLM implementation
        # Providers: "gemini", "openai", "anthropic", "huggingface"
```

#### 6. **app/vanna_service/service.py** (Text-to-SQL)
- **Purpose:** Core Vanna integration
- **Features:**
  - Generate SQL from natural language
  - Execute queries on source database
  - Train Vanna with DDL/documentation/SQL pairs
  - Vector store management

#### 7. **app/sql_guard.py** (Security)
- **Purpose:** SQL injection prevention
- **Features:**
  - Query parsing and validation
  - Restrict to SELECT statements
  - Block dangerous keywords (DROP, DELETE, etc.)
  - User-level filtering
  - Audit logging

---

## Database Models

### Admin Database (SQLite)

```sql
-- Users
CREATE TABLE user (
    id VARCHAR PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    password_hash VARCHAR NOT NULL,
    name VARCHAR,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Conversations
CREATE TABLE conversation (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL FOREIGN KEY,
    title VARCHAR NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES user(id)
);

-- Messages
CREATE TABLE message (
    id VARCHAR PRIMARY KEY,
    conversation_id VARCHAR NOT NULL FOREIGN KEY,
    role VARCHAR NOT NULL,  -- 'user' or 'assistant'
    content TEXT,
    sql_query TEXT,
    results JSON,
    visualization JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversation(id)
);

-- Training Items
CREATE TABLE training_item (
    id VARCHAR PRIMARY KEY,
    type VARCHAR,  -- 'ddl', 'documentation', 'sql_pair', 'knowledge_base'
    content TEXT,
    access VARCHAR DEFAULT 'public',  -- 'public' or 'authenticated'
    source_kind VARCHAR,
    source_name VARCHAR,
    source_file_type VARCHAR,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- User Settings
CREATE TABLE user_settings (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR UNIQUE NOT NULL FOREIGN KEY,
    audio_settings JSON,
    auto_speak BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES user(id)
);

-- Audit Logs
CREATE TABLE audit_log (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR FOREIGN KEY,
    action VARCHAR,
    resource VARCHAR,
    details JSON,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## API Architecture

### Request/Response Flow

```
1. Frontend sends HTTP request with JWT token
   ↓
2. Flask middleware validates token (JWT or microservice modes)
   ↓
3. Route handler processes request
   ↓
4. Business logic layer:
   - Authentication & Authorization
   - Input validation
   - Database operations
   - LLM integration
   ↓
5. Response formatted and returned
   ↓
6. Frontend displays results
```

### Error Handling Strategy

```python
# Centralized error handler pattern
@app.errorhandler(Exception)
def handle_error(error):
    return {
        "success": False,
        "error": str(error),
        "code": error_code,
        "timestamp": datetime.now()
    }, status_code
```

---

## Component Relationships

### Frontend Component Dependencies

```
Chat.jsx
├── Depends on: AuthContext, API client
├── Imports: MessageBubble, ChartRenderer
├── Uses: useEffect, useState, useRef
└── Communicates with: Backend /api/chat endpoint

Settings.jsx
├── Contains: 13 different tab components
├── Each tab depends on: Specific API endpoints
├── Uses: useEffect, useState, useMemo
└── Features: PDF generation, markdown rendering

API Client (api/client.js)
├── Wraps: axios
├── Adds: Authorization headers
├── Handles: Error responses
└── Methods: get(), post(), put(), delete()
```

### Backend Component Dependencies

```
run.py (Entry point)
└── Imports: create_app()
    └── app/__init__.py (App Factory)
        ├── Registers: Blueprints (auth, chat, training, etc.)
        ├── Sets up: Database (SQLAlchemy)
        ├── Initializes: JWT extension
        └── Blueprints:
            ├── api/auth.py (requires: models.py)
            ├── api/chat.py (requires: vanna_service, llm/factory)
            ├── api/training.py (requires: vanna_service, models.py)
            └── api/conversations.py (requires: conversation/manager)

vanna_service/service.py
├── Depends on: Vanna library
├── Uses: Vector store (ChromaDB/FAISS/Pinecone)
├── Integrates: LLM providers via llm/factory
└── Manages: Training data and SQL generation

conversation/manager.py
├── Depends on: SQLAlchemy models
├── Uses: Database session
├── Manages: Conversation persistence
└── Methods: CRUD operations
```

---

## Data Flow

### Query Processing Flow (Chat Endpoint)

```
1. Frontend: User sends query "What were Q1 2025 sales?"
   ↓
2. Frontend: HTTP POST /api/chat with query + conversation_id + token
   ↓
3. Backend: Validate JWT token
   ↓
4. Backend: Create/retrieve conversation context
   ↓
5. Backend: Vanna service analyzes query:
   - Generate SQL: "SELECT region, SUM(amount) FROM sales WHERE..."
   - Query source database
   - Retrieve results
   ↓
6. Backend: LLM processes results:
   - Generate natural language response
   - Format insights
   - Detect visualization needs
   ↓
7. Backend: ConversationManager persists:
   - User message
   - AI response with all metadata
   ↓
8. Backend: Return response to frontend:
   {
     message: "Q1 2025 sales were...",
     sql_query: "SELECT...",
     results: [...],
     visualization: {type: "bar", data: [...]},
     insights: [...]
   }
   ↓
9. Frontend: Render:
   - Display message
   - Show SQL query
   - Display results table
   - Render chart
   - Store audio settings for playback
   ↓
10. Frontend: User can listen, copy, or download
```

### Knowledge Base Upload Flow

```
1. User uploads file: company_handbook.pdf
   ↓
2. Frontend: multipart/form-data to /api/training/knowledge-base/upload
   ↓
3. Backend: Extract text from file:
   - PDF: pypdf extracts text
   - DOCX: python-docx extracts content
   - XLSX: openpyxl reads cells
   - PPTX: python-pptx reads slides
   - Images: Pillow + pytesseract OCR
   ↓
4. Backend: Tag with access level marker
   - Public: [stored as-is]
   - Authenticated: [ACCESS:AUTHENTICATED] prefix
   ↓
5. Backend: Vanna ingests text:
   - Split into chunks
   - Generate embeddings
   - Store in vector database
   ↓
6. Backend: Database record created for tracking
   ↓
7. Frontend: Show success message
```

---

## Development Setup

### Prerequisites

- Node.js 16+
- Python 3.9+
- PostgreSQL or MySQL (for source database)
- Git

### Frontend Setup

```bash
# Install dependencies
cd frontend
npm install

# Start development server
npm run dev
# Runs on http://localhost:5173

# Build for production
npm run build

# Preview production build
npm run preview
```

### Backend Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
cd backend
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run migrations (if needed)
flask db upgrade

# Start development server
python run.py
# Runs on http://localhost:5001
```

### Environment Variables

**Backend (.env):**
```bash
# Flask
SECRET_KEY=your-secret-key
FLASK_ENV=development
PORT=5001

# Databases
ADMIN_DB_URL=sqlite:///assistantai.db
SOURCE_DB_URL=postgresql://user:pass@localhost/dbname

# LLM Providers
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-key
OPENAI_API_KEY=your-key

# Vector Store
VECTOR_STORE=chromadb
CHROMA_PATH=./vanna_chroma

# Microservice Mode (optional)
MICROSERVICE_MODE=false
```

---

## Coding Standards

### Frontend

**File Organization:**
- Components in `src/components/` - Reusable UI components
- Pages in `src/pages/` - Full page components
- API client in `src/api/client.js`
- Utilities in `src/utils/`
- Styles use Tailwind CSS classes

**Naming Conventions:**
- Components: PascalCase (e.g., `MessageBubble.jsx`)
- Functions: camelCase (e.g., `handleClick()`)
- CSS classes: kebab-case (Tailwind default)
- Constants: UPPER_SNAKE_CASE

**React Best Practices:**
```javascript
// Use functional components with hooks
function ChatComponent() {
  const [state, setState] = useState(null);
  
  useEffect(() => {
    // Side effects here
  }, [dependencies]);
  
  return JSX;
}

// Use proper error handling
try {
  const response = await api.post('/endpoint', data);
} catch (error) {
  console.error('Error:', error);
  // Show user-friendly error message
}
```

### Backend

**File Organization:**
- Models in `app/models.py`
- Routes in `app/api/` (one file per resource)
- Business logic in `app/` root or separate modules
- Utilities in `app/` as needed

**Naming Conventions:**
- Modules: snake_case (e.g., `sql_guard.py`)
- Classes: PascalCase (e.g., `ConversationManager`)
- Functions: snake_case (e.g., `get_user_by_id()`)
- Constants: UPPER_SNAKE_CASE

**Flask Best Practices:**
```python
# Use blueprints for organization
from flask import Blueprint
bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@bp.route('/login', methods=['POST'])
def login():
    # Validate input
    data = request.get_json()
    if not data or not data.get('email'):
        return {'error': 'Missing fields'}, 400
    
    # Process
    try:
        user = authenticate_user(data['email'], data['password'])
        return {'token': generate_token(user)}, 200
    except Exception as e:
        return {'error': str(e)}, 500

# Use decorators for authentication
@require_auth
def protected_route():
    user_id = g.user_id  # From auth middleware
    # Process request
```

---

## Deployment

### Frontend Deployment

**Build:**
```bash
npm run build
# Creates dist/ folder with optimized files
```

**Deploy Options:**
- Vercel, Netlify (recommended for SPA)
- AWS S3 + CloudFront
- Docker container
- Traditional web server (nginx, Apache)

### Backend Deployment

**Containerization:**
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "run.py"]
```

**Deploy Options:**
- Heroku
- AWS Lambda + API Gateway
- AWS EC2 + RDS
- DigitalOcean App Platform
- Docker containers (Kubernetes)
- Traditional VPS with Gunicorn + Nginx

**Production Considerations:**
- Use HTTPS only
- Enable CORS properly
- Set secure headers
- Implement rate limiting
- Use connection pooling
- Enable database backups
- Monitor error logs
- Implement monitoring and alerting

---

## Performance Optimization

### Frontend

1. **Code Splitting** - Lazy load routes and components
2. **Image Optimization** - Compress and resize images
3. **Caching** - Service workers for offline support
4. **Minification** - Vite automatically minifies builds
5. **CDN** - Serve static assets from CDN

### Backend

1. **Database Indexes** - Index frequently queried columns
2. **Caching** - Redis for session/query caching
3. **Query Optimization** - Use efficient SQL
4. **Connection Pooling** - SQLAlchemy connection pools
5. **Async Operations** - Consider async endpoints for long operations
6. **Rate Limiting** - Prevent API abuse

---

## Testing Strategy

### Frontend Testing

```javascript
// Use Jest + React Testing Library
import { render, screen } from '@testing-library/react';
import ChatComponent from './Chat';

test('renders chat messages', () => {
  render(<ChatComponent />);
  expect(screen.getByText('Hello')).toBeInTheDocument();
});
```

### Backend Testing

```python
# Use pytest
import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app('testing')
    with app.test_client() as client:
        yield client

def test_login(client):
    response = client.post('/api/auth/login', 
        json={'email': 'user@test.com', 'password': 'pass'})
    assert response.status_code == 200
```

---

## Troubleshooting

### Common Development Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Port already in use | Another process using port | Kill process or use different port |
| Module not found | Missing dependencies | Run `npm install` or `pip install -r requirements.txt` |
| JWT token invalid | Token expired or malformed | Re-login to get new token |
| Database connection error | DB credentials wrong | Check `.env` and `SOURCE_DB_URL` |
| CORS error | Frontend and backend different origins | Enable CORS in Flask |
| Charts not rendering | Invalid data format | Check data has required columns |
| Vanna not generating SQL | Insufficient training data | Upload DDL and documentation |

---

## Contributing

### Pull Request Process

1. Create feature branch: `git checkout -b feature/feature-name`
2. Make changes following coding standards
3. Test thoroughly (frontend and backend)
4. Submit PR with description
5. Address review comments
6. Merge when approved

### Code Review Checklist

- ✅ Code follows naming conventions
- ✅ No console errors or warnings
- ✅ Error handling implemented
- ✅ Tests pass
- ✅ Documentation updated
- ✅ No hardcoded secrets

---

## Resources

- **Vanna Documentation:** https://docs.vanna.ai/
- **Flask Documentation:** https://flask.palletsprojects.com/
- **React Documentation:** https://react.dev/
- **SQLAlchemy Documentation:** https://docs.sqlalchemy.org/
- **Tailwind CSS:** https://tailwindcss.com/docs

---

**Happy coding! 🚀**
