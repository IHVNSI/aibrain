# assistantai — Vanna.ai Text-to-SQL (multi-turn)

A Flask + React app that turns natural-language questions into SQL using
[Vanna.ai](https://vanna.ai), with **multi-turn conversational** follow-ups,
a selectable vector store, and pluggable LLMs (free offline Hugging Face, or
cloud OpenAI / Gemini / Claude — default **Gemini**).

## Features
- **Vanna.ai text-to-SQL** with RAG training (DDL, documentation, question→SQL pairs, auto INFORMATION_SCHEMA).
- **Multi-turn conversations**: every new prompt is folded into the prior turns
  (continuation-first). The rewritten/merged prompt is logged to the terminal.
- **Selectable vector store**: ChromaDB (default, local/free), FAISS (local), Pinecone (cloud).
- **Pluggable LLM**: Hugging Face (offline/free), OpenAI, Gemini, Anthropic Claude.
- **Settings page** with tabs: LLM Config, DB Config, Vector DB, Training/RAG, Conversations, Caching/Metrics.
- **SQLite is the source of truth** for conversations, settings, audit and training metadata.
- Chat **Retry** button when the server is unreachable.
- **Microservice mode**: Run as a microservice that trusts tokens from your main auth server (no local login needed).

## Microservice Mode

Deploy this as a microservice to your existing app. The backend will:
- ✅ Accept tokens from your main authentication server
- ✅ Extract and track user identity per request
- ✅ Apply automatic data isolation (company/branch scoping)
- ❌ NOT handle login/registration (your main server does)

Setup in 30 seconds:
```bash
# In .env:
MICROSERVICE_MODE=true
MICROSERVICE_TOKEN_SECRET=your-shared-secret
MICROSERVICE_TOKEN_ALGORITHM=HS256
```

Then send requests with token:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:5001/api/chat/query
```

See [MICROSERVICE_SETUP.md](docs/MICROSERVICE_SETUP.md) for full guide and all validation strategies (RS256, OAuth2 introspection, etc).

## Layout
```
assistantai/
  backend/   Flask API (Vanna service, LLM providers, conversation manager)
  frontend/  React + Vite (Chat + Settings)
```

## Backend setup
```powershell
cd backend
python -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # then edit: API keys, SOURCE_DB_URL, provider
python run.py            # serves http://localhost:5001
```

Key `.env` values:
- `LLM_PROVIDER=gemini` and `GEMINI_API_KEY=...` (or switch to openai/anthropic/huggingface)
- `SOURCE_DB_URL=postgresql+psycopg2://user:pass@host:5432/db`
- `VECTOR_STORE=chromadb|faiss|pinecone`

## Frontend setup
```powershell
cd frontend
npm install
npm run dev   # http://localhost:5174 (proxies /api to :5001)
```

## Using it
1. Open **Settings → LLM Config**, pick a provider, paste the API key (or choose Hugging Face for offline).
2. **Settings → DB Config**: set the source database URL and Test.
3. **Settings → Vector DB**: choose ChromaDB/FAISS/Pinecone.
4. **Settings → Training/RAG**: add DDL / docs / Q-SQL pairs, or auto-train on INFORMATION_SCHEMA.
5. **Chat**: ask questions. Follow-ups (“and only the resolved ones?”, “now by month”)
   are interpreted as continuations; the merged prompt is shown and logged.

## Notes
- Claude uses prompt caching automatically (ephemeral cache on the system prefix).
- Hugging Face runs locally via `transformers`; the first use downloads the model to cache.
- Vanna training data is stored in the chosen vector store; SQLite mirrors metadata for the UI.
