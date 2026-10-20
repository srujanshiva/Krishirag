# KrishiRAG Architecture Specification

**Course / Hackathon:** CSE 473 · SIH25076  
**System:** KrishiRAG — AI-Based Farmer Query Support and Advisory System  
**Organization:** Government of Kerala (Agriculture, FoodTech & Rural Development)  
**Status:** Phase 8 Complete  

---

## 1. System Architecture Overview

KrishiRAG is designed as an enterprise-grade Retrieval-Augmented Generation (RAG) system with a bounded agentic orchestrator. The architecture decouples knowledge extraction, vector representation, conversational state, and LLM reasoning into clean, loosely coupled services.

```
                           +---------------------------+
                           |  Next.js 16 Web Frontend  |
                           |  (Farmer UI & Admin Desk) |
                           +-------------+-------------+
                                         |
                                HTTP / JSON API
                                         v
                           +---------------------------+
                           |    FastAPI Backend App    |
                           +-------------+-------------+
                                         |
             +---------------------------+---------------------------+
             |                           |                           |
             v                           v                           v
+------------------------+  +------------------------+  +------------------------+
|  PostgreSQL 17 (DB)    |  |   Qdrant Vector DB     |  |   Cloud LLM Gateway    |
|  - Documents Registry  |  |  - Cosine Distance     |  |  - Groq (Primary)      |
|  - Ingestion Jobs      |  |  - 384-dim Vectors     |  |  - Gemini (Fallback)   |
|  - Document Chunks     |  |  - Payload Metadata    |  |  - Bounded Retries     |
|  - Conversations       |  +------------------------+  +------------------------+
|  - Messages & Citations|               ^
|  - Farmer Feedback     |               | (FastEmbed BAAI/bge-small-en-v1.5)
+------------------------+               |
             ^                           |
             |       +-------------------+-------------------+
             +-------+  Asynchronous Ingestion Pipeline      |
                     |  - PDF Extraction & SHA-256 Hashing   |
                     |  - Deterministic Chunking (UUID v5)   |
                     |  - Idempotent Upsert & Deduplication  |
                     +---------------------------------------+
```

---

## 2. Component Design

### 2.1 API Layer (FastAPI)
- **`health.py`**: Liveness (`/api/v1/health`) and readiness (`/api/v1/ready`) probes verifying PostgreSQL, Qdrant, and LLM configuration without credential disclosure.
- **`chat.py`**: Primary advisory endpoint (`POST /api/v1/chat`). Enforces input limits (1-2000 chars), orchestrates dialogue sessions, and persists multi-turn history.
- **`feedback.py`**: Captures farmer ratings (1-5 stars) and qualitative feedback (`POST /api/v1/feedback`) linked directly to message IDs.
- **`conversations.py`**: Queries previous dialogue history (`GET /api/v1/conversations`).
- **`admin/ingestion.py`**: Admin endpoint for uploading agronomic PDFs (`POST /api/v1/admin/ingest-file`) with bearer token authentication, 50MB file size limits, and `%PDF` magic byte verification.

### 2.2 Agentic State Machine (`AgentOrchestrator`)
The agent orchestrator operates as a deterministic, bounded finite state machine with strict termination limits (maximum 10 iterations, 75.0s wall time):

```
                       [START]
                          |
                          v
                  [VALIDATE_INPUT]
                     /         \
         (adversarial)          (clean)
                   v              v
               [REJECT]   [ASSESS_CONTEXT]
                                  |
                                  v
                             [RETRIEVE] (tool: retrieve_knowledge)
                                  |
                                  v
                          [ASSESS_EVIDENCE] (tool: check_evidence_coverage)
                             /         \
               (insufficient)           (sufficient >= 0.38)
                           v              v
                  [SAFE_FALLBACK]    [CALL_LLM] (wrapped in XML delimiters)
                                          |
                                          v
                                 [VALIDATE_CITATIONS] (strip hallucinations)
                                          |
                                          v
                                      [RESPOND]
```

### 2.3 Knowledge Retrieval & Embeddings (RAG)
- **Embedding Model:** `BAAI/bge-small-en-v1.5` executing via ONNX runtime through `fastembed`.
  - Dimensions: 384
  - Footprint: ~67 MB
  - Inference: Local CPU, 0 cloud tokens consumed.
- **Vector Index:** Qdrant collection `agricultural_knowledge` configured with Cosine distance.
- **Chunking Strategy:** 400 token chunks with 80 token overlap. Deterministic vector ID generated via UUID v5 from document checksum and chunk index.

### 2.4 Citation & Grounding Assurance
- **`CitationValidator`:** Scans model response text for citations in format `[chunk_id]`.
- Strips any chunk IDs that do not exist in the retrieved evidence set for the current turn.
- Attaches structured metadata: document title, publisher, page number, section, source URL, and verbatim passage excerpt (first 300 characters).

### 2.5 Security & Prompt Guardrails
- **`PromptSafetyGuard`:** Intercepts prompt injection attacks, jailbreaks, and delimiter breakout attempts before LLM invocation.
- Evidence passages are HTML/XML-escaped and wrapped in `<evidence_corpus>` and `<evidence_passage>` tags marked as static non-executable reference data.

---

## 3. Data Model & Storage

### 3.1 Relational Schema (PostgreSQL 17)
- **`documents`**: Document metadata, source URL, publisher, and unique SHA-256 checksum.
- **`ingestion_jobs`**: Job status (`queued`, `processing`, `completed`, `failed`, `already_exists`), chunk counts, and error tracking.
- **`document_chunks`**: Text passages, section titles, page numbers, and unique Qdrant `vector_id`. Foreign key to `documents` with `ON DELETE CASCADE`.
- **`conversations`**: Dialogue session identifiers and timestamps.
- **`messages`**: Multi-turn dialogue entries with `role` (`user`/`assistant`), `citations` (`jsonb`), and `uncertainty` levels.
- **`feedback`**: Farmer ratings (1-5) and text comments linked to specific message IDs.
