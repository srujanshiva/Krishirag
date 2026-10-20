# KrishiRAG Architectural & Technical Decisions Record

**Course / Hackathon:** CSE 473 · SIH25076  
**System:** KrishiRAG — AI-Based Farmer Query Support and Advisory System  
**Last Updated:** 2026-10-21  

---

## 1. Decision Log

### ADR-01: Dual Cloud LLM Gateway Strategy (Groq Primary + Gemini Fallback)
- **Context:** Low-latency inference is essential for farmer advisories, but free-tier API quotas are strictly bounded (Groq: 200,000 tokens/day; Gemini: 20 requests/day).
- **Decision:** Implement an abstracted `LLMGateway` interface with automatic failover from `GroqGateway` (`qwen/qwen3.8-27b`) to `GeminiGateway` (`gemini-1.5-flash`).
- **Consequences:** Provides resilience against temporary provider outages; under complete daily quota depletion of both providers, the system cleanly surfaces HTTP 429 with actionable wait times rather than crashing or delivering ungrounded hallucinations.

### ADR-02: Local CPU Embeddings via FastEmbed (`BAAI/bge-small-en-v1.5`)
- **Context:** Cloud embedding APIs introduce latency, recurring cost, network fragility, and rate-limit exhaustion during bulk PDF ingestion.
- **Decision:** Utilize local ONNX-quantized `BAAI/bge-small-en-v1.5` embeddings (384 dimensions) via `fastembed`.
- **Consequences:** 100% free, offline, deterministic embedding generation; 0 cloud tokens consumed during document ingestion and search; fast CPU inference (~15ms per chunk).

### ADR-03: Qdrant as Primary Vector Database
- **Context:** Need a high-performance vector store with strong payload filtering, cosine similarity search, and low memory overhead in Docker.
- **Decision:** Deploy Qdrant in Docker (`qdrant/qdrant:latest`) on ports 6333/6334 with persistent storage volumes.
- **Consequences:** Highly efficient vector search; payload metadata holds chunk provenance (page numbers, section titles, document IDs) directly inside the index.

### ADR-04: Deterministic UUID v5 Chunk Identifiers
- **Context:** Ingestion pipelines must be idempotent: re-ingesting the same document or running multiple workers must not generate duplicate vector points or fragmented IDs.
- **Decision:** Generate vector IDs using UUID v5 derived from the document's SHA-256 checksum and chunk index: `uuid5(NAMESPACE_URL, f"{doc_checksum}:{chunk_index}")`.
- **Consequences:** Vector IDs are completely reproducible across systems and runs; Qdrant point upserts overwrite identically rather than creating orphan points.

### ADR-05: Strict Citation Stripping over Tolerant Hallucination
- **Context:** Generative LLMs frequently hallucinate bracketed citations (e.g. citing `[chunk_99]` when only 5 chunks were retrieved).
- **Decision:** Implement `CitationValidator` which treats retrieved chunk IDs as an explicit whitelist. Any cited ID not in the retrieved set is stripped from the response text and omitted from structured metadata.
- **Consequences:** 0.0% citation hallucination rate; responses only contain citations verifiable against authentic source pages.

### ADR-06: Bounded Agentic State Machine over Autonomous Loops
- **Context:** Unbounded agentic frameworks (AutoGPT, LangChain arbitrary loops) can enter infinite loops, blow through token budgets, and exhibit unpredictable latencies.
- **Decision:** Build an explicit, finite state machine (`AgentOrchestrator`) with a strict upper limit of 10 iterations and 75 seconds wall time.
- **Consequences:** Guaranteed termination; auditable state transitions; hard fallback to extension advisories when bounds are exceeded.

### ADR-07: Scope Gate Enforcement (No Unvetted Optional Integrations)
- **Context:** SIH problem statements often suggest speculative integrations (weather, market prices, speech-to-text, vision disease diagnosis) that lack verified free government APIs or models.
- **Decision:** Enforce a strict scope gate. Optional integrations remain unbuilt until free, licensed, and reliable APIs are confirmed.
- **Consequences:** 0 unvetted mock dependencies; 100% focus on rock-solid core RAG, grounding, citations, and security.

### ADR-08: Windows SelectorEventLoopPolicy Configuration
- **Context:** On Windows operating systems, Python 3.8+ uses `ProactorEventLoop` by default, which does not support asynchronous socket operations required by `psycopg` connection pools.
- **Decision:** Explicitly set `asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())` in `backend/run.py` and test initialization scripts.
- **Consequences:** Clean, error-free PostgreSQL async operations on Windows platforms.
