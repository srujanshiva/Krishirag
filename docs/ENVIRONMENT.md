# KrishiRAG Environment Configuration & Operational Runbook

**Course / Hackathon:** CSE 473 · SIH25076  
**System:** KrishiRAG — AI-Based Farmer Query Support and Advisory System  
**Last Updated:** 2026-10-21  

---

## 1. Environment Variables Specification

The application configuration is managed via `backend/app/config.py` using `pydantic-settings`. All settings are read from `.env` in the project root.

| Variable | Required | Default / Format | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | `postgresql+psycopg://krishirag:krishirag@localhost:5432/krishirag` | Asynchronous PostgreSQL connection string. |
| `QDRANT_URL` | Yes | `http://localhost:6333` | Qdrant vector database HTTP endpoint. |
| `QDRANT_COLLECTION` | Yes | `agricultural_knowledge` | Name of the primary knowledge base collection. |
| `LLM_PROVIDER` | Yes | `groq` | Active LLM gateway provider (`groq` or `gemini`). |
| `GROQ_API_KEY` | Conditional | `gsk_...` | Groq cloud API key (required if `LLM_PROVIDER=groq`). |
| `GOOGLE_API_KEY` | Conditional | `AIza...` / `AQ....` | Google Gemini API key (fallback provider). |
| `LLM_MODEL` | No | `qwen/qwen3.8-27b` | Model identifier on primary LLM provider. |
| `LLM_TIMEOUT_SECONDS` | No | `30` | Per-request LLM timeout limit before triggering `LLMTimeoutError`. |
| `LLM_MAX_RETRIES` | No | `2` | Retry attempts on transient provider failures. |
| `EMBEDDING_MODEL` | No | `BAAI/bge-small-en-v1.5` | FastEmbed model identifier (local ONNX). |
| `APP_ENV` | No | `development` | Runtime environment (`development`, `test`, `production`). |
| `SECRET_KEY` | Yes | Secure random string | Application session encryption key. |
| `ALLOWED_HOSTS` | No | `localhost,127.0.0.1` | Comma-delimited list of permitted host headers. |
| `ADMIN_TOKEN` | Yes | `local-dev-admin-token` | Bearer token required for `/api/v1/admin/*` endpoints. |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Ollama native service HTTP base URL. |
| `OLLAMA_MODEL` | No | `qwen2.5:3b` | Target open-weight model tag pulled in Ollama. |
| `OLLAMA_TIMEOUT_SECONDS` | No | `60` | Request timeout for local CPU inference. |
| `ENABLE_LOCAL_LLM_FALLBACK` | No | `false` | Enable automatic failover to Ollama when cloud APIs hit 429. |
| `OFFLINE_MODE` | No | `false` | Strictly prohibit cloud API calls; route only to local Ollama. |

---

## 2. Infrastructure Services (Docker Compose)

Launch with:
```bash
docker compose up -d
```

| Service | Container Name | Image | Host Ports | Volume Mount | Health Check |
|---|---|---|---|---|---|
| PostgreSQL | `krishirag_postgres` | `postgres:17-alpine` | `5432:5432` | `postgres_data` | `pg_isready -U krishirag -d krishirag` |
| Qdrant | `krishirag_qdrant` | `qdrant/qdrant:latest` | `6333:6333`, `6334:6334` | `qdrant_data` | TCP socket probe on 6333 |

---

## 3. Operating System Specific Requirements

### Windows 10/11
1. **Asyncio Event Loop Policy:**
   - Asynchronous `psycopg` connection pooling requires `WindowsSelectorEventLoopPolicy`.
   - Always start the backend using:
     ```bash
     python backend/run.py
     ```
   - Do NOT run `uvicorn backend.app.main:app` directly in Windows shells without configuring the event loop policy.

2. **Node.js Environment Path:**
   - If Node.js is installed via `winget` or in `C:\Program Files\nodejs`, ensure the directory is appended to `$env:PATH` in PowerShell:
     ```powershell
     $env:PATH = "C:\Program Files\nodejs;" + $env:PATH
     ```

---

## 4. Operational Health & Diagnostics Endpoints

- **Liveness Probe:** `GET http://localhost:8000/api/v1/health`
  - Output: `{"status": "ok", "version": "0.1.0"}`
- **Readiness Probe:** `GET http://localhost:8000/api/v1/ready`
  - Output: `{"db": "ok", "vector_store": "ok", "llm_configured": true, "knowledge_base": "populated"}`
- **Interactive Swagger Documentation:** `http://localhost:8000/docs`
- **Frontend Advisory Interface:** `http://localhost:3000`
