# VoxSell — Autonomous AI Sales Voice Agent

VoxSell is an enterprise-grade autonomous AI sales voice agent designed for sub-1.5s voice-to-voice response latency, real-time BANT lead qualification, multilingual code-switching (English, Hindi, Punjabi), RAG knowledge retrieval, and automated calendar/CRM synchronization.

---

## Architecture Overview

```
voxsell/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app initialization, CORS, lifespan
│   │   ├── config.py            # Pydantic-settings loading .env
│   │   ├── api/                 # REST & WebSocket route handlers
│   │   ├── voice/               # Streaming STT (Deepgram) & TTS pipelines
│   │   ├── agent/               # Streaming LLM orchestrator & BANT qualifier
│   │   ├── rag/                 # ChromaDB vector store & retrieval
│   │   ├── crm/                 # Postgres CRM & HubSpot sync
│   │   ├── calendar/            # Google Calendar booking integration
│   │   ├── analytics/           # Post-call summarization & metrics
│   │   ├── db/                  # Async database session & connection pooling
│   │   └── models/              # SQLAlchemy 2.0 ORM schemas
│   ├── migrations/              # Alembic migration scripts
│   ├── tests/                   # Pytest suite
│   ├── requirements.txt         # Pinned backend dependencies
│   ├── Dockerfile               # Multi-stage Python 3.11 container
│   └── alembic.ini              # Database migration configuration
├── frontend/                    # React + Vite dashboard
├── knowledge_base/              # Product catalogue, pricing, and FAQ docs
├── docs/                        # Architecture diagrams and design notes
├── docker-compose.yml           # Backend, Postgres, Redis, ChromaDB
├── .env.example                 # Environment variables blueprint
└── Makefile                     # Developer automation commands
```

---

## Quickstart & Setup

### 1. Environment Configuration
Copy `.env.example` to `.env` in the `voxsell/` root:
```bash
cp .env.example .env
```
Fill in your API keys (Deepgram, OpenAI / Groq / Gemini, etc.).

### 2. Run with Docker Compose (Recommended)
Launch all four core services (FastAPI, PostgreSQL 16, Redis 7, ChromaDB):
```bash
docker compose up -d
```
Inspect logs:
```bash
docker compose logs -f backend
```

### 3. Run Locally (Without Docker)
1. Install Python dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
2. Run database migrations:
   ```bash
   alembic upgrade head
   ```
3. Start the FastAPI server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

---

## Verification & Testing

### 1. Health Endpoint Check
Query the `/health` endpoint to verify service liveness:
```bash
curl -X GET http://localhost:8000/health
```
**Expected Response:**
```json
{
  "status": "ok",
  "app": "VoxSell",
  "version": "0.1.0",
  "timestamp": "2026-11-25T17:30:00.000000Z"
}
```

Or run the self-contained verification script:
```bash
python backend/verify_health.py
```

### 2. Run Unit Test Suite
```bash
pytest backend/tests/ -v
```

---

## Technical Viva Defenses (Architectural Rationale)

- **Why `pydantic-settings` instead of raw `os.getenv`?**
  *Defense*: `pydantic-settings` provides fail-fast startup type validation, parsing complex data structures (like CORS JSON origin arrays), and eliminating runtime `KeyError` or type-casting exceptions across distributed services.
- **Why Async SQLAlchemy with Connection Pooling?**
  *Defense*: Traditional synchronous database calls block the ASGI event loop during high-concurrency voice streaming. Asyncpg with a pooled connection strategy (`pool_size=20`, `max_overflow=10`) guarantees non-blocking I/O across thousands of concurrent calls.
- **Why Separate Redis from PostgreSQL?**
  *Defense*: Redis handles millisecond-level transient call turn buffers, pub/sub barge-in signals, and active WebSocket state. PostgreSQL guarantees ACID persistence for completed calls, audit transcripts, and CRM leads.
