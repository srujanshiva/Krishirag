# KrishiRAG — AI-Based Farmer Query Support and Advisory System

**CSE 473 · Smart India Hackathon (SIH 2024 / SIH25076)**  
**Problem Statement ID:** `SIH25076`  
**Theme:** Agriculture, FoodTech & Rural Development  
**Organization:** Government of Kerala  

---

## Overview

KrishiRAG is an enterprise-grade, retrieval-augmented agricultural advisory system designed to provide smallholder and commercial farmers with actionable, verifiable agronomic advice. Built with an Agentic RAG architecture, KrishiRAG synthesizes information exclusively from vetted agricultural repositories (such as ICAR, TNAU Agritech Portal, KAU, and MoA&FW package of practices) while enforcing strict citation attribution, grounded answers, and guardrails against hallucinations.

---

## Project Status

| Phase | Description | Status |
|---|---|---|
| **Phase 0** | Codebase Audit & Implementation Plan | **COMPLETE** |
| **Phase 1** | Foundation: Project Scaffolding, Docker, Config, DB & Health Probes | **COMPLETE** |
| **Phase 2** | Knowledge Ingestion: Genuine Agronomic PDFs, Chunking & Qdrant Indexing | **COMPLETE** (19/19 tests passing, 101 authentic vectors indexed) |
| **Phase 4** | Agentic Query Orchestrator, Citations & Guardrails | **COMPLETE** (44/44 tests passing, bounded state machine + injection filters) |
| **Phase 5** | Web Interface (Farmer UI, Citations Viewer & Admin Ingestion Portal) | **COMPLETE** (Next.js 16 App Router UI, live citations inspector) |
| **Phase 7** | Automated E2E Verification & Benchmark Suite | **COMPLETE** (5/5 live E2E passing, 10/10 benchmark tests passing, 0% hallucination) |
| **Phase 8** | Comprehensive Documentation & Submission Runbook | *Next up* |

---

## Architecture & Technology Stack

- **Backend Framework:** FastAPI 0.110+ (Python 3.12)
- **Database & ORM:** PostgreSQL 17 (via Docker Compose) + SQLAlchemy 2.0 + Alembic
- **Vector Database:** Qdrant (via Docker Compose)
- **Embeddings:** `fastembed` with `BAAI/bge-small-en-v1.5` (local ONNX runtime, 384 dimensions)
- **Primary LLM:** Groq API (`qwen/qwen3.8-27b`)
- **Fallback LLM:** Google Gemini API (`gemini-1.5-flash`)
- **Testing:** Pytest, pytest-asyncio, httpx

---

## Local Development Setup

### 1. Prerequisites
- Python 3.12+
- Docker & Docker Desktop (running)
- Git

### 2. Environment Configuration
Copy the template and configure your local settings:
```bash
cp .env.example .env
```
Ensure your `.env` contains your verified API keys (`GROQ_API_KEY`, `GOOGLE_API_KEY`). **Never commit `.env` to version control.**

### 3. Start Infrastructure Services
Launch PostgreSQL and Qdrant in Docker:
```bash
docker compose up -d
```
Check health:
```bash
docker ps
```
Both `krishirag_postgres` and `krishirag_qdrant` should show `(healthy)`.

### 4. Run Database Migrations
Apply Alembic migrations to create the database schema:
```bash
cd backend
python -m alembic upgrade head
```

### 5. Run Backend Server
```bash
python backend/run.py
```
- Interactive Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- Liveness Probe: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- Readiness Probe: [http://localhost:8000/api/v1/ready](http://localhost:8000/api/v1/ready)

### 6. Run Frontend Web Interface
```bash
cd frontend
npm run dev
```
- Web Application: [http://localhost:3000](http://localhost:3000)

### 7. Run Test Suite
```bash
python -m pytest backend/tests -v
```

---

## Database Schema (Initial)

- `documents`: Authoritative agricultural publications and documents registry (checksum, publisher, license).
- `ingestion_jobs`: Asynchronous tracking for document extraction, chunking, and embedding runs.
- `document_chunks`: Extracted text passages mapped to stable vector IDs in Qdrant with page/section provenance.
- `conversations`: Farmer advisory interaction sessions.
- `messages`: Multi-turn dialogue messages with structured citations (`jsonb`) and uncertainty levels.
- `feedback`: Farmer ratings (1 to 5) and advisory feedback.
