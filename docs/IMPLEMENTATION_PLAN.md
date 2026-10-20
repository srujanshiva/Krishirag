# KrishiRAG — Implementation Plan (UPDATED)
**CSE 473 · SIH25076 · AI-Based Farmer Query Support and Advisory System**
**Audit date:** 2026-10-20 · **Updated:** 2026-10-20 · **Status:** Phase 2 COMPLETE — ready for Phase 3

---

## CONFIRMED DECISIONS (All Blocking Questions Resolved)

| Question | Answer |
|---|---|
| Q1 — LLM Provider | Groq API (primary) + Google Gemini (fallback). Keys stored in gitignored .env. |
| Q2 — Node.js | APPROVED — install via winget for Next.js frontend |
| Q3 — Docker Desktop | CONFIRMED running — PostgreSQL + Qdrant via Docker Compose |
| Q4 — Official SIH25076 PS | Full PDF not available. Using conservative scope from spec PDF (SIH25076 metadata confirmed). |

---

## 1. Verified Current State

### 1.1 Repository Inventory

| Item | Status |
|---|---|
| Source code | NONE — greenfield build |
| Backend (FastAPI) | MISSING |
| Frontend (React/Next.js) | MISSING |
| Database models / migrations | MISSING |
| Vector store setup (Qdrant) | MISSING |
| Ingestion pipeline | MISSING |
| LLM gateway | MISSING |
| Tests | MISSING |
| Docker Compose | MISSING |
| `.env` | WRITTEN (gitignored) — Groq + Gemini keys wired |
| `.env.example` | WRITTEN (placeholders only) |
| `.gitignore` | WRITTEN |

---

### 1.2 Runtime and Package Audit

#### Confirmed available

| Tool | Version | Status |
|---|---|---|
| Python | 3.12.0 | Ready |
| Node.js | — | Will install via winget (Phase 5) |
| Docker + Compose | 29.8.0 / v5.5.1 | Running |
| Git | 2.54.0 | Ready |

#### Pre-installed Python packages (relevant, all confirmed importable)

fastapi 0.139.0, uvicorn 0.51.0, sqlalchemy 2.0.51, alembic 1.20.0,
psycopg 3.3.6, psycopg2-binary 2.9.12, pydantic 2.13.4,
pydantic-settings 2.14.2, qdrant-client 1.19.1, fastembed 0.8.1,
pypdf 5.9.0, pdfplumber 0.11.10, pytest 9.1.1, httpx 0.28.1,
loguru 0.7.3, python-dotenv 1.2.2

#### To install in Phase 1

openai (Groq uses OpenAI-compatible client), pytest-asyncio, pytest-cov,
aiofiles, google-generativeai (Gemini fallback)

#### LLM credentials

| Provider | Key name | Status |
|---|---|---|
| Groq (primary) | GROQ_API_KEY | Stored in .env — to be verified |
| Google Gemini (fallback) | GOOGLE_API_KEY | Stored in .env |
| LLM model | llama-3.1-70b-versatile | Default |
| Embedding | BAAI/bge-small-en-v1.5 (local ONNX, 67 MB) | No API key needed |

#### System resources

RAM: 16 GB · Free disk: ~169 GB · GPU: Intel Iris Xe (API-based LLM only)

---

## 2. Architecture (Confirmed Greenfield Build)

```
KrishiRAG/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app factory
│   │   ├── config.py             # pydantic-settings, reads .env
│   │   ├── api/v1/
│   │   │   ├── health.py         # GET /api/v1/health, /ready
│   │   │   ├── chat.py           # POST /api/v1/chat
│   │   │   ├── conversations.py  # GET /api/v1/conversations[/{id}]
│   │   │   ├── feedback.py       # POST /api/v1/feedback
│   │   │   └── admin/
│   │   │       └── ingestion.py  # POST/GET /api/v1/admin/ingestion-jobs
│   │   ├── agent/
│   │   │   ├── orchestrator.py   # Bounded state machine
│   │   │   ├── tools.py          # Typed tool registry
│   │   │   └── safety.py         # Prompt injection defence
│   │   ├── rag/
│   │   │   ├── ingestion.py      # PDF ingestion worker
│   │   │   ├── chunker.py        # Chunking + stable IDs
│   │   │   ├── embedder.py       # fastembed wrapper
│   │   │   ├── vector_store.py   # Qdrant client wrapper
│   │   │   └── retriever.py      # Retrieval
│   │   ├── llm/
│   │   │   └── gateway.py        # Provider abstraction (Groq/Gemini/OpenAI/HF)
│   │   ├── citations/
│   │   │   └── validator.py      # Citation ID => retrieved chunk validation
│   │   ├── db/
│   │   │   ├── models.py         # SQLAlchemy models
│   │   │   ├── session.py        # Async session factory
│   │   │   └── repository.py     # CRUD helpers
│   │   └── schemas/
│   │       ├── chat.py
│   │       ├── ingestion.py
│   │       └── citations.py
│   ├── migrations/
│   │   ├── env.py
│   │   └── versions/
│   │       └── 0001_initial.py
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── unit/
│   │   │   ├── test_chunker.py
│   │   │   ├── test_citation_validator.py
│   │   │   ├── test_tool_schemas.py
│   │   │   └── test_ingestion_idempotency.py
│   │   ├── api/
│   │   │   ├── test_health.py
│   │   │   ├── test_chat.py
│   │   │   ├── test_ingestion_api.py
│   │   │   └── test_feedback.py
│   │   ├── rag/
│   │   │   ├── test_retrieval.py
│   │   │   └── test_embedder.py
│   │   ├── db/
│   │   │   ├── test_migrations.py
│   │   │   └── test_persistence.py
│   │   ├── integration/          # require real providers, marked @pytest.mark.integration
│   │   │   ├── test_llm_gateway.py
│   │   │   └── test_end_to_end.py
│   │   └── security/
│   │       └── test_prompt_injection.py
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── alembic.ini
│   └── pytest.ini
├── frontend/                     # Next.js (Phase 5 — after Node.js install)
├── data/sources/                 # Real agricultural PDFs (Phase 2)
├── docs/
│   ├── IMPLEMENTATION_PLAN.md    # This file
│   ├── ARCHITECTURE.md           # Phase 8
│   ├── DATA_SOURCES.md           # Phase 2
│   ├── DECISIONS.md              # Phase 8
│   ├── ENVIRONMENT.md            # Phase 8
│   └── TEST_REPORT.md            # Phase 7
├── docker-compose.yml
├── .env                          # GITIGNORED — real keys
├── .env.example                  # Safe to commit — placeholders only
├── .gitignore
└── README.md
```

---

## 3. Confirmed Technology Stack

| Component | Choice | License | Cost |
|---|---|---|---|
| Backend | FastAPI + uvicorn | MIT | Free |
| ORM + migrations | SQLAlchemy 2 + Alembic | MIT | Free |
| Database | PostgreSQL 16 (Docker) | PostgreSQL License | Free |
| Vector store | Qdrant (Docker) | Apache 2.0 | Free |
| Embeddings | fastembed + BAAI/bge-small-en-v1.5 | MIT/Apache | Free, local ONNX |
| PDF extraction | pypdf + pdfplumber | MIT | Free |
| LLM (primary) | Groq API — llama-3.1-70b-versatile | Free tier | Free, rate-limited |
| LLM (fallback) | Google Gemini — gemini-1.5-flash | Free tier | Free, rate-limited |
| Frontend | Next.js 14 + React | MIT | Free |
| Testing | pytest + httpx | MIT | Free |
| E2E testing | Playwright | MIT | Free |
| Logging | loguru | MIT | Free |

---

## 4. Ordered Implementation Phases

### Phase 0 — Audit and Plan [COMPLETE]

Deliverables: .gitignore, .env (gitignored), .env.example, docs/IMPLEMENTATION_PLAN.md
Gate: Awaiting final approval to proceed to Phase 1.

---

### Phase 1 — Foundation: Project Structure, Config, DB, Health [COMPLETE]
**Executed:** 2026-10-20 · **Status:** PASSED (7/7 tests green, PostgreSQL + Qdrant healthy)

**Scope:** Start the app locally with PostgreSQL + Qdrant (Docker Compose), run migrations
cleanly, and respond to health/readiness endpoints. All config via .env only.

**Files to create:**

```
docker-compose.yml
backend/requirements.txt
backend/requirements-dev.txt
backend/app/__init__.py
backend/app/main.py
backend/app/config.py
backend/app/api/__init__.py
backend/app/api/v1/__init__.py
backend/app/api/v1/health.py
backend/app/db/__init__.py
backend/app/db/models.py
backend/app/db/session.py
backend/alembic.ini
backend/migrations/env.py
backend/migrations/script.py.mako
backend/migrations/versions/0001_initial.py
backend/pytest.ini
backend/tests/__init__.py
backend/tests/conftest.py
backend/tests/api/__init__.py
backend/tests/api/test_health.py
backend/tests/db/__init__.py
backend/tests/db/test_migrations.py
README.md (initial, honest)
```

**Docker Compose services:**
- postgres:16-alpine — port 5432, named volume
- qdrant/qdrant:latest — port 6333/6334, named volume
- Both with health checks

**DB schema (all in 0001_initial):**

```sql
-- Document registry
CREATE TABLE documents (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title         TEXT NOT NULL,
  publisher     TEXT,
  source_url    TEXT,
  language      TEXT DEFAULT 'en',
  checksum_sha256 TEXT UNIQUE NOT NULL,
  retrieved_at  TIMESTAMPTZ,
  ingestion_status TEXT NOT NULL DEFAULT 'pending',
    -- pending | processing | completed | failed | already_exists
  license_note  TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Ingestion job tracking
CREATE TABLE ingestion_jobs (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id   UUID REFERENCES documents(id),
  status        TEXT NOT NULL DEFAULT 'queued',
    -- queued | processing | completed | failed
  chunk_count   INTEGER,
  error_message TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at   TIMESTAMPTZ
);

-- Document chunks (provenance preserved through ingestion)
CREATE TABLE document_chunks (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id   UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  chunk_index   INTEGER NOT NULL,
  chunk_text    TEXT NOT NULL,
  vector_id     TEXT UNIQUE NOT NULL,  -- Qdrant point ID (stable)
  page_number   INTEGER,
  section       TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(document_id, chunk_index)
);

-- Conversation and message persistence
CREATE TABLE conversations (
  id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE messages (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role            TEXT NOT NULL,  -- user | assistant
  content         TEXT NOT NULL,
  citations       JSONB DEFAULT '[]',
  uncertainty     TEXT DEFAULT 'none',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE feedback (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
  rating     SMALLINT CHECK (rating BETWEEN 1 AND 5),
  comment    TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**API endpoints (Phase 1):**

```
GET /api/v1/health   -> {"status": "ok", "version": "0.1.0"}
GET /api/v1/ready    -> {"db": "ok"|"error", "vector_store": "ok"|"error",
                         "llm_configured": true|false}
                        (no secrets or connection strings in response)
```

**Acceptance criteria:**
- [x] docker compose up -d succeeds; both containers healthy (`krishirag_postgres` and `krishirag_qdrant` healthy)
- [x] alembic upgrade head runs clean from empty DB (verified by test)
- [x] alembic downgrade base && alembic upgrade head — no errors (verified clean migration roundtrip)
- [x] GET /api/v1/health -> 200 {"status": "ok", "version": "0.1.0"}
- [x] GET /api/v1/ready -> 200 with honest dependency statuses (`db: ok`, `vector_store: ok`, `llm_configured: true`)
- [x] pytest tests/api/test_health.py tests/db/test_migrations.py — 7 passed, 0 failed (GREEN)

---

### Phase 2 — Real Knowledge Ingestion [COMPLETE]
**Executed:** 2026-10-20 · **Status:** PASSED (19/19 tests green, 101 authentic vectors indexed in Qdrant)

**Scope:** Ingest genuine agricultural PDFs from authoritative public sources.
Implement extraction, chunking, checksumming, deduplication, local fastembed embeddings,
Qdrant indexing, and verified idempotency.

**Files to create:**

```
backend/app/rag/__init__.py
backend/app/rag/ingestion.py
backend/app/rag/chunker.py
backend/app/rag/embedder.py
backend/app/rag/vector_store.py
backend/app/api/v1/admin/__init__.py
backend/app/api/v1/admin/ingestion.py
backend/app/schemas/__init__.py
backend/app/schemas/ingestion.py
backend/tests/unit/__init__.py
backend/tests/unit/test_chunker.py
backend/tests/unit/test_ingestion_idempotency.py
backend/tests/rag/__init__.py
backend/tests/rag/test_embedder.py
data/sources/                     (real PDFs fetched here)
docs/DATA_SOURCES.md
```

**Planned genuine sources (all will be verified for access and license before download):**

| Source | Type | URL |
|---|---|---|
| ICAR — Crop Production Guide | PDF | https://icar.org.in/content/crop-production |
| Kerala Agri Dept — Package of Practices | PDF | https://keralaagriculture.gov.in/ |
| TNAU Agritech — Crop Management | HTML/PDF | https://agritech.tnau.ac.in/ |
| KVK Thrissur — Advisories | PDF | https://kvkthrissur.icar.gov.in/ |
| ICAR-RCER — Paddy production | PDF | https://rcer.icar.gov.in/ |

**Chunking parameters:**
- Model: BAAI/bge-small-en-v1.5 (dim=384)
- Chunk size: 400 tokens (~320 words)
- Overlap: 80 tokens
- Stable chunk ID: hex(sha256(doc_checksum + ":" + str(chunk_index)))
- Metadata stored: doc_id, chunk_index, page_number, section, source_url, publisher, retrieved_at

**Deduplication:**
- Document level: UNIQUE constraint on checksum_sha256 in documents table
- Chunk level: Qdrant upsert using stable vector_id (idempotent by design)
- Job returns already_exists status if checksum already in DB

**Admin API:**

```
POST /api/v1/admin/ingestion-jobs
  Header: Authorization: Bearer {ADMIN_TOKEN}
  Body: { source_url: string } | multipart file upload
  Response: { job_id: uuid, status: "queued" }

GET /api/v1/admin/ingestion-jobs/{id}
  Header: Authorization: Bearer {ADMIN_TOKEN}
  Response: { id, status, document_id, chunk_count, error_message, created_at, finished_at }
```

**Acceptance criteria:**
- [x] Ingest a real PDF -> job completed, 101 chunks in DB, 101 vectors in Qdrant (TNAU Rice Guide)
- [x] Ingest same PDF twice -> second job status "already_exists", zero new DB rows, zero new vectors (verified in `test_ingestion_idempotency`)
- [x] Qdrant collection "agricultural_knowledge" with vectors of dim=384 (verified in `test_qdrant_collection_lifecycle`)
- [x] Empty DB -> readiness endpoint shows knowledge_base: "empty", not a crash (and "populated" when documents are present)
- [x] pytest tests/unit/test_chunker.py tests/unit/test_ingestion_idempotency.py tests/rag/ — all 19 tests GREEN

---

### Phase 3 — RAG + Real LLM Gateway + Citation Validation

**Scope:** Retrieval from Qdrant, Groq LLM gateway (OpenAI-compatible client),
grounded prompt, citation ID validation, uncertainty handling.

**Files to create:**

```
backend/app/rag/retriever.py
backend/app/llm/__init__.py
backend/app/llm/gateway.py
backend/app/citations/__init__.py
backend/app/citations/validator.py
backend/app/api/v1/chat.py
backend/app/api/v1/conversations.py
backend/app/api/v1/feedback.py
backend/app/schemas/chat.py
backend/app/schemas/citations.py
backend/tests/rag/test_retrieval.py
backend/tests/unit/test_citation_validator.py
backend/tests/api/test_chat.py
backend/tests/api/test_feedback.py
backend/tests/integration/__init__.py
backend/tests/integration/test_llm_gateway.py
```

**LLM gateway design:**

```python
class LLMGateway(ABC):
    async def complete(self, system: str, user: str,
                       context_chunks: list[ChunkResult]) -> LLMResponse: ...

class GroqGateway(LLMGateway):   # uses openai client with base_url=https://api.groq.com/openai/v1
class GeminiGateway(LLMGateway): # uses google-generativeai
class OpenAIGateway(LLMGateway): # standard openai
class HFGateway(LLMGateway):     # huggingface inference API
```

Error handling:
- Missing key -> HTTP 503, error_code LLM_NOT_CONFIGURED
- Quota exceeded -> HTTP 429, error_code LLM_QUOTA_EXCEEDED
- Timeout -> HTTP 504, error_code LLM_TIMEOUT
- Malformed output -> HTTP 500, error_code LLM_INVALID_RESPONSE
- NEVER silent fallback to canned response

**Citation validation:**
- Parse [chunk_id] references from LLM output
- Validate each against the set of chunk_ids retrieved for this request
- Strip any that are not in the retrieved set; log warning with count

**POST /api/v1/chat — request:**

```json
{
  "question": "string (1-2000 chars)",
  "conversation_id": "uuid | null",
  "crop": "string | null",
  "location": "string | null"
}
```

**POST /api/v1/chat — response:**

```json
{
  "request_id": "uuid",
  "answer": "string",
  "citations": [
    {
      "chunk_id": "string",
      "document_title": "string",
      "publisher": "string",
      "source_url": "string | null",
      "publication_date": "string | null",
      "page_number": "integer | null",
      "section": "string | null",
      "excerpt": "string (first 300 chars of chunk)"
    }
  ],
  "uncertainty": "none | low | high",
  "conversation_id": "uuid",
  "message_id": "uuid",
  "retrieval_score": "float | null",
  "evidence_count": "integer"
}
```

**Acceptance criteria:**
- Real question + populated KB -> grounded answer, all citation IDs from retrieved chunks only
- Empty KB -> uncertainty "high", answer text recommends KVK/officer, citations []
- LLM key missing -> HTTP 503, error_code LLM_NOT_CONFIGURED
- Model-invented citation ID -> stripped from response, logged
- pytest tests/rag/test_retrieval.py tests/unit/test_citation_validator.py tests/api/test_chat.py — GREEN (no LLM key needed for most)
- pytest -m integration tests/integration/test_llm_gateway.py — GREEN (requires GROQ_API_KEY)

---

### Phase 4 — Bounded Agentic Workflow

**Scope:** Explicit orchestrator state machine, typed tool registry, iteration limits,
logging, prompt injection defence.

**Files to create:**

```
backend/app/agent/__init__.py
backend/app/agent/orchestrator.py
backend/app/agent/tools.py
backend/app/agent/safety.py
backend/tests/unit/test_tool_schemas.py
backend/tests/security/__init__.py
backend/tests/security/test_prompt_injection.py
```

**State machine:**

```
START
  |
  v
VALIDATE_INPUT -------> REJECT (if invalid/too-long question)
  |
  v
ASSESS_CONTEXT
  |                 |
  v                 v
RETRIEVE     ASK_CLARIFICATION (if crop/region needed for safety)
  |
  v
ASSESS_EVIDENCE ------> SAFE_FALLBACK (if coverage too low and safety-critical)
  |
  v
CALL_LLM (tool: retrieve_knowledge, check_evidence_coverage)
  |
  v
VALIDATE_CITATIONS
  |
  v
RESPOND
```

**Tool registry:**

```python
# Only these tools exposed to the state machine / model
REGISTERED_TOOLS = {
    "retrieve_knowledge": Tool(
        name="retrieve_knowledge",
        input_schema=RetrieveInput,   # query: str, top_k: int = 5
        output_schema=list[ChunkResult],
        timeout_seconds=10.0,
    ),
    "check_evidence_coverage": Tool(
        name="check_evidence_coverage",
        input_schema=CoverageInput,   # chunks: list[ChunkResult]
        output_schema=CoverageReport, # sufficient: bool, score: float
        timeout_seconds=2.0,
    ),
}
# NOT exposed: db writes, file writes, shell, unconstrained HTTP
```

**Limits:** max_iterations=5, max_wall_seconds=45
**Safety:** chunk text wrapped in XML-safe delimiters; no model instruction can override system prompt

**Acceptance criteria:**
- Normal question -> RESPOND state reached within iteration limit
- Iteration limit exceeded -> SAFE_FALLBACK state, safe answer returned
- Prompt injection in retrieved chunk text -> tool not misused
- Tool calls logged: name, sanitized args, duration, outcome
- pytest tests/unit/test_tool_schemas.py tests/security/test_prompt_injection.py — GREEN

---

### Phase 5 — Complete UI Flow

**Scope:** Wire Next.js frontend to real backend endpoints. Show answer, citations,
loading/error/empty states, conversation persistence.

**Prerequisite:** Node.js installed (will install at start of Phase 5).

**Key components:**

```
frontend/
├── src/app/
│   ├── page.tsx              # Main chat page
│   └── layout.tsx
├── src/components/
│   ├── ChatInput.tsx         # Question input, optional crop/location fields
│   ├── AnswerDisplay.tsx     # Answer with source-evidence distinction
│   ├── CitationCard.tsx      # Per-citation: title, publisher, date, URL, excerpt
│   ├── ConversationHistory.tsx
│   ├── LoadingSpinner.tsx
│   ├── ErrorBanner.tsx       # LLM error, network error, quota error
│   └── EmptyKnowledgeBase.tsx
├── src/lib/
│   └── api.ts               # Typed fetch wrapper for all endpoints
└── src/types/index.ts
```

**UI states to implement:**
- Idle: question input ready
- Loading: spinner during API call
- Success: answer + citation cards
- LLM unavailable: error banner (not blank screen)
- Empty KB: explicit "no documents ingested" state
- Network/timeout error: error banner with retry option
- Conversation history: session messages listed

**Acceptance criteria:**
- Submit question -> real answer + citations rendered from backend
- LLM unavailable -> error banner shown
- Empty KB -> EmptyKnowledgeBase component shown
- Playwright E2E test: submit -> response -> citations visible -> PASS

---

### Phase 6 — Optional Scope Decision (Gate Only)

No implementation. After Phase 5 passes, present each optional feature with its
confirmed free source, license, test strategy, and implementation cost before approving.

| Feature | Safe implementation gate |
|---|---|
| Weather | Official PS confirms + Open-Meteo free API confirmed |
| Government schemes | Official source URL + update strategy confirmed |
| Voice input | Web Speech API browser support confirmed; MVP passed |
| Image disease triage | Real validated model/dataset confirmed |
| Market prices | Agmarknet or NHM feed confirmed accessible |
| Officer escalation | Real contact directory confirmed |

---

### Phase 7 — Verification and Test Report

Full suite from clean state:

```bash
# Infrastructure
docker compose down -v && docker compose up -d
sleep 10   # wait for health checks

# Migrations (clean)
cd backend
alembic downgrade base
alembic upgrade head

# Offline tests (no LLM key needed)
pytest tests/unit/ tests/api/ tests/rag/ tests/db/ tests/security/ \
       -v --cov=app --cov-report=term-missing

# Integration tests (require GROQ_API_KEY)
pytest tests/integration/ -v -m integration

# Duplicate ingestion regression
pytest tests/unit/test_ingestion_idempotency.py -v -s

# E2E (requires full running stack + Node.js)
npx playwright test
```

docs/TEST_REPORT.md: exact commands, stdout, pass/fail counts, BLOCKED items, limitations.

---

### Phase 8 — Handover Documentation

Complete all docs: README.md (exact setup/run/test), docs/ARCHITECTURE.md,
docs/DATA_SOURCES.md, docs/DECISIONS.md, docs/ENVIRONMENT.md, docs/TEST_REPORT.md.

---

## 5. Environment Variables (Names Only — Values in Gitignored .env)

```
DATABASE_URL          postgresql+psycopg://user:pass@host:port/dbname
QDRANT_URL            http://localhost:6333
QDRANT_COLLECTION     agricultural_knowledge
LLM_PROVIDER          groq | gemini | openai | huggingface
GROQ_API_KEY          [stored in .env, gitignored]
GOOGLE_API_KEY        [stored in .env, gitignored]
OPENAI_API_KEY        [not set — paid, excluded]
HF_TOKEN              [not set]
LLM_MODEL             llama-3.1-70b-versatile (groq default)
LLM_TIMEOUT_SECONDS   30
LLM_MAX_RETRIES       2
EMBEDDING_MODEL       BAAI/bge-small-en-v1.5
APP_ENV               development | test | production
SECRET_KEY            [stored in .env]
ALLOWED_HOSTS         localhost,127.0.0.1
ADMIN_TOKEN           [stored in .env]
```

---

## 6. Testing Strategy

| Category | Tool | LLM key? | Phase | Pass threshold |
|---|---|---|---|---|
| Unit (chunker, citation, tools) | pytest | No | 1-4 | 100% |
| API (health, chat, ingestion) | pytest + httpx TestClient | No | 1-3 | 100% |
| RAG (retrieval, embedder) | pytest | No | 2-3 | 100% |
| DB (migrations, persistence) | pytest | No | 1-2 | 100% |
| Security (prompt injection) | pytest | No | 4 | 100% |
| Integration (LLM gateway) | pytest @integration | YES | 3 | PASS or BLOCKED |
| E2E (UI to API to LLM) | Playwright | YES | 5 | PASS or BLOCKED |
| Regression (duplicate ingestion) | pytest | No | 2 | 100% |

**Pass gate (overall):** all non-integration tests GREEN, no xfail without justification,
coverage >= 70% on backend/app/, integration tests separately reported.

---

## 7. Remaining Risks

| Risk | Mitigation |
|---|---|
| Groq free tier rate limits during CI | Small integration suite; offline fixtures for unit tests |
| Agricultural PDFs behind login or ToS-restricted | Verify ToS before downloading; document in DATA_SOURCES.md |
| fastembed first download (67 MB) fails | Cache in local path; pre-download in setup script |
| Docker networking on Windows | Use host.docker.internal where needed |

---

## 8. Scope Gate (Final)

Optional features will NOT be implemented until:
1. Core MVP (Phases 1-5) passes all acceptance criteria
2. Each optional feature is explicitly approved with free source, license, and test plan

Conservative scope = LLM + RAG + Agentic AI + genuine sources + citations + real integrations
+ automated tests + working frontend + honest docs.

---

*Phase 0 complete. .env written (gitignored). .env.example written (committed).
All blocking questions resolved. Awaiting explicit "approve Phase 1" to begin coding.*
