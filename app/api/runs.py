from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.entities import AgentRun, AgentStep, Approval, LLMCall, Memory
from app.db.session import get_db
from app.schemas.runs import AgentRunRead, AgentStepRead

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("/{run_id}", response_model=AgentRunRead)
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(AgentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/{run_id}/steps", response_model=list[AgentStepRead])
def get_steps(run_id: str, db: Session = Depends(get_db)):
    if not db.get(AgentRun, run_id):
        raise HTTPException(status_code=404, detail="Run not found")
    return list(db.scalars(select(AgentStep).where(AgentStep.run_id == run_id).order_by(AgentStep.step_number)).all())


@router.get("/{run_id}/trace")
def get_trace(run_id: str, db: Session = Depends(get_db)):
    run = db.get(AgentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    steps = db.scalars(select(AgentStep).where(AgentStep.run_id == run_id).order_by(AgentStep.step_number)).all()
    approvals = db.scalars(select(Approval).where(Approval.run_id == run_id).order_by(Approval.requested_at)).all()
    memories = db.scalars(select(Memory).where(Memory.run_id == run_id).order_by(Memory.created_at)).all()
    llm_calls = db.scalars(select(LLMCall).where(LLMCall.run_id == run_id).order_by(LLMCall.created_at)).all()
    return {
        "run": AgentRunRead.model_validate(run).model_dump(mode="json"),
        "steps": [AgentStepRead.model_validate(s).model_dump(mode="json") for s in steps],
        "approvals": [
            {"id": a.id, "action": a.action, "payload": a.action_payload, "status": a.status, "requested_at": a.requested_at, "resolved_at": a.resolved_at, "resolved_by": a.resolved_by, "executed_at": a.executed_at}
            for a in approvals
        ],
        "memories": [{"type": m.memory_type, "key": m.key, "value": m.value, "created_at": m.created_at} for m in memories],
        "llm_calls": [
            {"step_number": c.step_number, "model": c.model_name, "latency_ms": c.latency_ms, "input_tokens": c.input_tokens, "output_tokens": c.output_tokens, "retries": c.retry_count, "validation_error": c.validation_error}
            for c in llm_calls
        ],
    }


@router.get("/{run_id}/metrics")
def get_run_metrics(run_id: str, db: Session = Depends(get_db)):
    run = db.get(AgentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    steps = db.scalars(select(AgentStep).where(AgentStep.run_id == run_id)).all()
    llm_calls = db.scalars(select(LLMCall).where(LLMCall.run_id == run_id)).all()
    started = run.started_at
    ended = run.completed_at or datetime.now(started.tzinfo if started else None)
    duration_ms = (ended - started).total_seconds() * 1000 if started else None
    return {
        "run_id": run_id,
        "status": run.status,
        "step_count": len(steps),
        "tool_calls": sum(1 for s in steps if s.tool_name),
        "tool_failures": sum(1 for s in steps if s.tool_name and s.status == "FAILED"),
        "tool_retries": sum(s.retry_count for s in steps),
        "tool_latency_ms": round(sum(s.latency_ms or 0 for s in steps if s.tool_name), 2),
        "llm_calls": len(llm_calls),
        "llm_latency_ms": round(sum(c.latency_ms for c in llm_calls), 2),
        "input_tokens": sum(c.input_tokens or 0 for c in llm_calls),
        "output_tokens": sum(c.output_tokens or 0 for c in llm_calls),
        "duration_ms": round(duration_ms, 2) if duration_ms is not None else None,
    }
