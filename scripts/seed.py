from app.db.session import SessionLocal, init_db
from app.rag.ingest import ingest_default_runbooks


if __name__ == "__main__":
    init_db()
    db = SessionLocal()
    try:
        count = ingest_default_runbooks(db)
        print(f"Ingested or verified {count} built-in runbooks.")
    finally:
        db.close()
