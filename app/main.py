# app/main.py - FastAPI application entry point

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Financial Intelligence System")
    from app.db.database import init_db
    init_db()
    logger.info("Database ready")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Personal Financial Intelligence System",
    description="Analyze personal cashflows, detect anomalies, and generate AI-powered insights.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router import must come after app creation to avoid circular references
from app.api.routes import router  # noqa: E402
app.include_router(router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    from app.config import config

    uvicorn.run(
        "app.main:app",
        host=config.app.backend_host,
        port=config.app.backend_port,
        reload=True,
        log_level=config.app.log_level.lower(),
    )
