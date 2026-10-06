import os
from pathlib import Path

TEST_DB = Path(__file__).resolve().parent / "reliableops_test.db"
if TEST_DB.exists():
    TEST_DB.unlink()

os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{TEST_DB}"
os.environ["REDIS_URL"] = "redis://localhost:6399/15"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
os.environ["AUTO_SEED_KNOWLEDGE"] = "true"

import pytest
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, init_db
from app.rag.ingest import ingest_default_runbooks


@pytest.fixture(scope="session", autouse=True)
def initialize_database():
    init_db()
    db = SessionLocal()
    try:
        ingest_default_runbooks(db)
    finally:
        db.close()
    yield
    if TEST_DB.exists():
        TEST_DB.unlink()


@pytest.fixture
def db() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
