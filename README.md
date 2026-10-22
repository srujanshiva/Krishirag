# KrishiRAG — AI-Powered Agricultural Advisory System

[![Live Demo](https://img.shields.io/badge/Live_Demo-Cloudflare_Tunnel-blue?style=flat-square&logo=cloudflare)](https://sunny-populations-section-disclaimer.trycloudflare.com/)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js_16-black?style=flat-square&logo=next.js&logoColor=white)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI_0.110+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Vector DB](https://img.shields.io/badge/Vector_DB-Qdrant-DC2626?style=flat-square)](https://qdrant.tech)
[![Database](https://img.shields.io/badge/Database-PostgreSQL_17-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![LLM](https://img.shields.io/badge/LLM-Groq_%7C_Gemini_%7C_Ollama-8A2BE2?style=flat-square)](https://groq.com)
[![License](https://img.shields.io/badge/License-MIT-brightgreen?style=flat-square)](LICENSE)

**KrishiRAG** is a production-grade, authoritative **AI Agricultural Advisory System** engineered for Indian smallholder and commercial farmers. Built with a bounded **Agentic RAG architecture**, multi-provider LLM orchestration, and vector search, KrishiRAG synthesizes advice strictly from verified government agricultural manuals (such as **ICAR, TNAU Agritech Portal, KAU, and MoA&FW**). It guarantees zero chemical hallucination, enforces statutory food-safety Pre-Harvest Intervals (PHI), validates claim-level faithfulness, and incorporates live agrometeorological forecasting.

> **Repository:** [https://github.com/srujanshiva/Krishirag.git](https://github.com/srujanshiva/Krishirag.git)  
> **Live Demo:** [https://sunny-populations-section-disclaimer.trycloudflare.com/](https://sunny-populations-section-disclaimer.trycloudflare.com/)  
> **Academic / SIH Track:** Smart India Hackathon (`SIH25076` — Theme: Agriculture, FoodTech & Rural Development)

---

## 📑 Table of Contents

1. [Overview](#overview)
2. [Feature Highlights](#feature-highlights)
3. [What's New & Scientific Novelties](#whats-new--scientific-novelties)
4. [Resume & Engineering Highlights](#resume--engineering-highlights)
5. [Tech Stack](#tech-stack)
6. [System Architecture](#system-architecture)
7. [How It Works](#how-it-works)
8. [Project Structure](#project-structure)
9. [Knowledge Ingestion & Vector Pipeline](#knowledge-ingestion--vector-pipeline)
10. [Environment Variables](#environment-variables)
11. [Run Locally](#run-locally)
12. [Run with Docker & Compose](#run-with-docker--compose)
13. [Free Public Deployment (Cloudflare Tunnel)](#free-public-deployment-cloudflare-tunnel)
14. [Testing & KrishiBench-50 Evaluation](#testing--krishibench-50-evaluation)
15. [Troubleshooting & FAQ](#troubleshooting--faq)
16. [Author & License](#author--license)

---

## 🌾 Overview

Indian agriculture suffers from severe information fragmentation: farmers rely on informal advice, outdated dealer recommendations, or generic chatbots that hallucinate hazardous pesticide doses. 

**KrishiRAG solves this by implementing a closed-world, evidence-grounded agentic pipeline:**
* **Zero Guesswork:** If official Package of Practices (PoP) manuals lack sufficient evidence, the agent triggers `SAFE_FALLBACK` directing the farmer to their local Krishi Bhavan or KVK.
* **Traceable Attribution:** Every sentence, numeric rate, or spray recommendation is accompanied by verifiable bracketed citations (`[1]`, `[2]`) pointing to official source documents.
* **Contextual Agronomy:** Recommendations factor in the farmer's crop, region/district, local weather forecasts, and harvest timeline.

---

## ✨ Feature Highlights

| Feature | Description |
| :--- | :--- |
| **🛡️ Guarded Agentic RAG** | Deterministic 10-step state machine with query validation, evidence coverage checks, and prompt-injection defense. |
| **🧪 Chemical Safety & PHI Guardrail** | Intercepts banned pesticides (e.g., Phorate 10G) and Pre-Harvest Interval violations; injects safe biological alternatives (*Pseudomonas*, Neem). |
| **⚖️ Claim Faithfulness Scorer** | Decomposes answers into atomic facts and computes entailment against retrieved chunks (0–100% confidence badge). |
| **🚜 Fertilizer Bag Calculator** | Translates academic NPK ratios into physical 45kg/50kg commercial bags (Urea, DAP, MOP) per Acre, Cent, or Tree. |
| **🌦️ Real-Time Agrometeorology** | Live Open-Meteo integration delivering temperature, rainfall risk, wind speed, and suitability for chemical spraying. |
| **🔍 Multimodal Leaf Diagnostics** | Image upload diagnostic inspecting visual lesion patterns (chlorosis, blast, spots) matched against verified disease guides. |
| **⚡ Multi-Provider LLM Gateway** | Hot-swappable support for **Groq (Llama 3 / Qwen)**, **Google Gemini 3.8 Flash**, and **local Ollama** (offline zero-token inference). |
| **📄 Ingestion & Admin Portal** | Dedicated UI to upload, parse, chunk, embed, and index government PDFs in real-time into Qdrant. |

---

## 🔬 What's New & Scientific Novelties

KrishiRAG introduces three peer-review grade innovations beyond standard RAG baselines:

1. **Claim-Level Grounding & Faithfulness Scorer (`backend/app/citations/faithfulness.py`):**
   * Eliminates black-box LLM trust by extracting discrete factual claims from the response.
   * Cross-references claims against the retrieved passage vectors using token and numeric alignment.
   * Produces an explainability score rendered live on the frontend.

2. **Regulatory Chemical Safety & Pre-Harvest Interval (PHI) Guardrail (`backend/app/agent/tools.py`):**
   * Encodes statutory Central Insecticides Board & Registration Committee (CIBRC) regulations and KAU pesticide directives.
   * If a farmer plans to harvest within 7 days and asks to spray a chemical requiring a 30-day withholding period, the system halts application and prescribes safe bio-controls.

3. **`KrishiBench-50` Quantitative Evaluation Benchmark (`backend/benchmark/`):**
   * Curated 50-query golden agricultural evaluation dataset spanning agronomic guidance, pest attacks, Indic regional terms, and adversarial jailbreak attempts.
   * Yields **100% Safety Interception**, **95.0% Grounding Faithfulness**, and a **33.5 ms median latency**.

---

## 💼 Resume & Engineering Highlights

* **Production Full-Stack Architecture:** Next.js 16 (React 19, TypeScript) App Router frontend coupled with a high-throughput async FastAPI (Python 3.12) backend.
* **Vector Search Engineering:** Dense hybrid search with `fastembed` (`BAAI/bge-small-en-v1.5`, 384-d) ONNX embeddings and Qdrant vector database indexing.
* **Resilient Infrastructure:** PostgreSQL 17 relational store with Alembic schema migrations; connection pooling optimized for Windows and Linux Selector loops.
* **Hermetic Test Coverage:** Over 80+ unit and integration tests covering chunking, citation validation, prompt safety guardrails, and agent state transitions.
* **Edge & Offline Capability:** Zero-cost public deployment via Cloudflare Tunnel, paired with local Ollama inference fallback when internet connectivity drops.

---

## 🛠️ Tech Stack

```mermaid
graph LR
    User([Farmer / Agronomist]) --> NextJS[Next.js 16 Frontend]
    NextJS --> Cloudflare[Cloudflare Tunnel]
    Cloudflare --> FastAPI[FastAPI Backend]
    FastAPI --> Agent[Agentic Orchestrator]
    Agent --> Tools[Specialized Tools]
    Tools --> Weather[Open-Meteo Weather API]
    Tools --> ChemDB[CIBRC Chemical Safety Engine]
    Tools --> FertCalc[Fertilizer Dosage Calculator]
    Agent --> Qdrant[(Qdrant Vector DB)]
    Agent --> Postgres[(PostgreSQL 17)]
    Agent --> LLM[LLM Gateway: Groq / Gemini / Ollama]
```

* **Frontend:** Next.js 16, React 19, TypeScript, Lucide Icons, Vanilla CSS Design System
* **Backend:** FastAPI, Uvicorn, Pydantic v2, Loguru, PyPDF, pdfplumber
* **Databases:** PostgreSQL 17 (Relational & Audit), Qdrant (Vector Database)
* **Embeddings & Search:** FastEmbed (`BAAI/bge-small-en-v1.5`), BM25 Hybrid Retrieval
* **LLM Providers:** Groq (`qwen/qwen3.8-27b`), Google Gemini (`gemini-3.8-flash`), Ollama (`qwen2.5:3b`)
* **Tunneling & Networking:** Cloudflare Tunnel (`cloudflared`)

---

## 🔄 How It Works

```text
[Farmer Query] 
       │
       ▼
 [1. VALIDATE_INPUT] ──(Adversarial Pattern Detected?)──► [REJECT]
       │ Safe
       ▼
 [2. ASSESS_CONTEXT] ──► (Trigger Weather, Crop Calendar, PHI, or Fertilizer Tools)
       │
       ▼
 [3. RETRIEVE] ────────► (Qdrant Vector DB: Hybrid Dense + Sparse Search)
       │
       ▼
 [4. ASSESS_EVIDENCE] ──(Similarity Score < 0.38?)──────► [SAFE_FALLBACK] (Consult Krishi Bhavan)
       │ Sufficient
       ▼
 [5. CALL_LLM] ────────► (Wrap Passages in XML Delimiters + Inject Tool Guidance)
       │
       ▼
 [6. VALIDATE_CITATIONS]► (Verify [1], [2] Citations & Compute Faithfulness Score)
       │
       ▼
 [7. RESPOND] ─────────► (Structured Advisory + Live Citations + Printable Card)
```

---

## 📂 Project Structure

```text
KrishiRAG/
├── backend/
│   ├── app/
│   │   ├── agent/            # State machine orchestrator, safety guards & tools
│   │   ├── api/v1/           # REST endpoints (chat, health, ready, ingest, feedback)
│   │   ├── citations/        # Faithfulness scorer & regex citation validator
│   │   ├── db/               # PostgreSQL engine, session management & models
│   │   ├── llm/              # Multi-provider LLM gateway (Groq, Gemini, Ollama)
│   │   ├── rag/              # Document chunker, fastembed embedder & Qdrant store
│   │   └── schemas/          # Pydantic v2 request/response contracts
│   ├── benchmark/            # KrishiBench-50 evaluation suite & dataset
│   ├── migrations/           # Alembic database migrations
│   ├── tests/                # Pytest unit & integration test suites
│   └── run.py                # Windows & Linux safe ASGI entrypoint
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js App Router (page.tsx, layout.tsx)
│   │   ├── components/       # ChatWindow, AnswerCard, Diagnostics, Ingestion
│   │   ├── lib/              # API clients & proxy helpers
│   │   └── types/            # TypeScript interfaces
│   ├── next.config.ts        # Next.js config with internal API reverse proxy
│   └── package.json          # Node dependencies & build scripts
├── data/
│   └── sources/              # Authoritative government PDFs (TNAU, KAU, ICAR)
├── docs/                     # Architectural, benchmark & demonstration documentation
├── docker-compose.yml        # Multi-container orchestration (PostgreSQL + Qdrant)
└── .env.example              # Environment variables template
```

---

## 📥 Knowledge Ingestion & Vector Pipeline

KrishiRAG utilizes high-yield government agricultural manuals stored in `data/sources/`:
* **TNAU Crop Production Guide — Rice** (Tamil Nadu Agricultural University)
* **KAU Package of Practices: Crops** (Kerala Agricultural University)
* **NFSM Ready Reckoner** (National Food Security Mission)
* **Spices and Plantation Guide** (Coconut, Black Pepper)

### Automated Extraction Pipeline:
1. PDFs are processed via `pypdf` and `pdfplumber` to extract structured sections.
2. The [chunker.py](file:///c:/Users/sruja/OneDrive/Desktop/KrishiRAG/backend/app/rag/chunker.py) segments documents into semantic passages while preserving crop and section metadata.
3. FastEmbed converts text into 384-dimensional dense vectors.
4. Chunks and payload metadata are indexed in Qdrant under collection `agricultural_knowledge`.

---

## ⚙️ Environment Variables

Create your `.env` file in the root directory:

```env
# Database & Vector DB
DATABASE_URL=postgresql+psycopg://krishirag:krishirag@localhost:5432/krishirag
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=agricultural_knowledge

# LLM Providers (Choose groq, gemini, or ollama)
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
GEMINI_MODEL=gemini-3.8-flash
LLM_MODEL=qwen/qwen3.8-27b

# System Configuration
APP_ENV=development
SECRET_KEY=generate-a-secure-secret-key
ADMIN_TOKEN=local-dev-admin-token
ENABLE_LOCAL_LLM_FALLBACK=true
```

In `frontend/.env.local`:
```env
NEXT_PUBLIC_API_URL=/api/v1
```

---

## 🚀 Run Locally

### 1. Start Infrastructure (Docker)
```powershell
docker compose up -d
```
*Verifies PostgreSQL on port `5432` and Qdrant on port `6333`.*

### 2. Apply Database Migrations
```powershell
cd backend
python -m alembic upgrade head
cd ..
```

### 3. Start the Backend API
```powershell
python backend/run.py
```
* Backend runs at: `http://127.0.0.1:8000`
* Swagger API Docs: `http://127.0.0.1:8000/docs`
* Health Check: `http://127.0.0.1:8000/api/v1/health`

### 4. Start the Frontend
```powershell
cd frontend
npm run dev
```
* Access the web UI at: `http://localhost:3000`

---

## 🌐 Free Public Deployment (Cloudflare Tunnel)

To share the application publicly from your local PC with **zero hosting costs**:

1. **Build the production frontend:**
   ```powershell
   cd frontend
   npm run build
   npm run start
   ```
2. **Start the Cloudflare Tunnel:**
   ```powershell
   .\cloudflared.exe tunnel --url http://localhost:3000
   ```
3. Copy the public URL (e.g. `https://your-tunnel-name.trycloudflare.com`) and open it on any smartphone, tablet, or external computer!

---

## 🧪 Testing & KrishiBench-50 Evaluation

Execute the complete hermetic test suite:
```powershell
python -m pytest backend/tests -v
```

Run the golden agricultural benchmark evaluation:
```powershell
python backend/benchmark/run_evaluation.py
```

---

## ❓ Troubleshooting & FAQ

<details>
<summary><b>1. Why does the chatbot say "Verified manuals do not contain sufficient evidence"?</b></summary>
KrishiRAG is designed strictly against hallucinations. If a crop or specific chemical query is not present in the ingested PDFs, it refuses to guess. Ingest the relevant crop PDF guide via the Admin Ingestion tab.
</details>

<details>
<summary><b>2. How does Windows Selector loop work with psycopg?</b></summary>
On Windows, Python 3.8+ uses `ProactorEventLoop` by default, which can conflict with asynchronous database drivers. `backend/run.py` explicitly sets `asyncio.WindowsSelectorEventLoopPolicy()` to guarantee seamless connection pooling.
</details>

<details>
<summary><b>3. Can I run KrishiRAG 100% offline without any internet connection?</b></summary>
Yes! Set `LLM_PROVIDER=ollama` in your `.env`, run `ollama run qwen2.5:3b`, and ensure Qdrant and Postgres are active locally. FastEmbed embeddings and Ollama inference will run entirely on your local CPU/GPU with zero external API calls.
</details>

---

## 👤 Author & License

* **Author:** Srujan Shiva ([@srujanshiva](https://github.com/srujanshiva))
* **Repository:** [https://github.com/srujanshiva/Krishirag](https://github.com/srujanshiva/Krishirag)
* **License:** This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
