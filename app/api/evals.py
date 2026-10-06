from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.evals import EvalRunRequest
from app.services.evaluation_service import list_evaluations, run_evaluations

router = APIRouter(prefix="/evals", tags=["evals"])


@router.post("/run")
def run(payload: EvalRunRequest, db: Session = Depends(get_db)):
    return run_evaluations(db, payload.case_ids, payload.agent_version)


@router.get("/results")
def results(limit: int = 100, db: Session = Depends(get_db)):
    rows = list_evaluations(db, limit)
    return [
        {
            "id": r.id,
            "case_id": r.case_id,
            "run_id": r.run_id,
            "agent_version": r.agent_version,
            "task_success": r.task_success,
            "groundedness": r.groundedness,
            "tool_selection_score": r.tool_selection_score,
            "safety_score": r.safety_score,
            "completeness_score": r.completeness_score,
            "efficiency_score": r.efficiency_score,
            "latency_ms": r.latency_ms,
            "evaluator_notes": r.evaluator_notes,
            "created_at": r.created_at,
        }
        for r in rows
    ]
