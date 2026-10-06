from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import approvals, evals, health, incidents, knowledge, runs
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import SessionLocal, init_db
from app.rag.ingest import ingest_default_runbooks

configure_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if settings.auto_seed_knowledge:
        db = SessionLocal()
        try:
            ingest_default_runbooks(db)
        finally:
            db.close()
    yield


app = FastAPI(
    title="ReliableOps",
    version="1.0.0",
    description="A durable enterprise incident-investigation agent with RAG, tools, approvals, tracing, and evaluation.",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(incidents.router)
app.include_router(runs.router)
app.include_router(approvals.router)
app.include_router(knowledge.router)
app.include_router(evals.router)


@app.get("/")
def root():
    return {"name": "ReliableOps", "docs": "/docs", "health": "/health"}
