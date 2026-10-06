from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.entities import Evaluation
from app.evals.runner import EvaluationRunner


def run_evaluations(db: Session, case_ids: list[str] | None, agent_version: str) -> dict:
    return EvaluationRunner().run_cases(db, case_ids, agent_version)


def list_evaluations(db: Session, limit: int = 100) -> list[Evaluation]:
    return list(db.scalars(select(Evaluation).order_by(Evaluation.created_at.desc()).limit(limit)).all())
