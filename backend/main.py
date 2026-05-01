import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from routers import upload, dashboard
from routers import portfolio

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

app = FastAPI(
    title="Personal Financial Analytics API",
    version="1.0.0",
    description="Deterministic personal finance analytics — no AI, all data-driven.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, tags=["Ingestion"])
app.include_router(dashboard.router, tags=["Analytics"])
app.include_router(portfolio.router, tags=["Portfolio"])


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}
