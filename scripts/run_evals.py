import json

from app.db.session import SessionLocal, init_db
from app.rag.ingest import ingest_default_runbooks
from app.evals.runner import EvaluationRunner


if __name__ == "__main__":
    init_db()
    db = SessionLocal()
    try:
        ingest_default_runbooks(db)
        result = EvaluationRunner().run_cases(db)
        print(json.dumps(result, indent=2, default=str))
    finally:
        db.close()
