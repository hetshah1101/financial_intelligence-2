# Personal Financial Intelligence System

A modular, production-oriented MVP that ingests personal transaction data, computes financial analytics, detects anomalies, and generates AI-powered insights via a local Ollama LLM (with OpenAI fallback).

---

## Architecture

```
financial_intelligence/
├── app/
│   ├── main.py                         # FastAPI entry point
│   ├── config.py                       # Centralized config (env-driven)
│   ├── api/
│   │   └── routes.py                   # All API endpoints
│   ├── db/
│   │   └── database.py                 # SQLite init + connection manager
│   ├── models/
│   │   └── schemas.py                  # Pydantic request/response models
│   ├── services/
│   │   ├── ai_service.py               # AI abstraction (Ollama + OpenAI)
│   │   ├── analytics_orchestrator.py   # Pipeline coordinator
│   │   ├── cashflow_engine.py
│   │   ├── category_engine.py
│   │   ├── trend_engine.py
│   │   ├── anomaly_engine.py
│   │   ├── behavior_engine.py
│   │   ├── efficiency_engine.py
│   │   └── savings_engine.py
│   └── utils/
│       └── ingestion.py
├── frontend/
│   └── streamlit_app.py
├── sample_data/
│   └── transactions.csv
├── requirements.txt
├── .env.example
└── README.md
```

---

## Setup

### 1. Install dependencies
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure
```bash
cp .env.example .env
```

### 3. Start Ollama
```bash
ollama serve
ollama pull llama3:8b
```

### 4. Start backend
```bash
uvicorn app.main:app
# API at http://localhost:8000 | Docs at http://localhost:8000/docs
```

### 5. Start frontend
```bash
cd frontend && streamlit run streamlit_app.py
# Dashboard at http://localhost:8501
```

### 6. Load sample data
```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@sample_data/transactions.csv"
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/upload | Initial full dataset load |
| POST | /api/v1/update | Incremental monthly update |
| GET  | /api/v1/dashboard | Full metrics payload |
| GET  | /api/v1/insights/{month} | AI insights (cached) |
| GET  | /api/v1/months | List months with data |
| GET  | /api/v1/health | Health check |

Add `?refresh=true` to insights endpoint to regenerate.

---

## Key Design Decisions

- **AI never calculates** — all numbers come from Python engines; AI only interprets structured JSON
- **Idempotent uploads** — duplicate detection via unique index on (date, amount, type, category, description, account)
- **Incremental recompute** — only affected months are reprocessed on update
- **Graceful AI degradation** — dashboard works even if Ollama/OpenAI are unavailable
- **PostgreSQL-ready** — SQLite used for zero-config MVP; schema is standard SQL

---

## Analytics Engines

| Engine | Capability |
|--------|-----------|
| cashflow | Income / expense / investment / net savings / savings rate |
| category | Per-category spend + % of total expenses |
| trend | MoM % change + N-month rolling averages |
| anomaly | current > 1.4x avg(last 3 months) |
| behavior | High-frequency spends + weekend vs weekday ratio |
| efficiency | vs. historical median (flags >20% deviation) |
| savings | Optimal spend bands per category vs income |
