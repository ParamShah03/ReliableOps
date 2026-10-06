from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.state import InvestigationContext
from app.db.models.entities import AgentRun, AgentStep, Approval, Incident, Memory
from app.services.memory_service import retrieve_similar_incidents, upsert_memory


def build_context(db: Session, run: AgentRun, max_steps: int) -> InvestigationContext:
    incident = db.get(Incident, run.incident_id)
    if not incident:
        raise ValueError(f"Incident not found: {run.incident_id}")

    similar = retrieve_similar_incidents(f"{incident.title} {incident.description}")
    for item in similar:
        upsert_memory(db, run.id, "long_term_incident", item["id"], item)
    db.flush()

    steps = db.scalars(select(AgentStep).where(AgentStep.run_id == run.id).order_by(AgentStep.step_number)).all()
    memories = db.scalars(select(Memory).where(Memory.run_id == run.id).order_by(Memory.created_at)).all()
    approvals = db.scalars(select(Approval).where(Approval.run_id == run.id).order_by(Approval.requested_at)).all()

    return InvestigationContext(
        run_id=run.id,
        incident_id=incident.id,
        title=incident.title,
        description=incident.description,
        severity=incident.severity,
        current_step=run.current_step,
        prior_steps=[
            {
                "step_number": s.step_number,
                "step_type": s.step_type,
                "reasoning_summary": s.reasoning_summary,
                "tool_name": s.tool_name,
                "tool_input": s.tool_input,
                "tool_output": s.tool_output,
                "status": s.status,
                "error_message": s.error_message,
            }
            for s in steps
        ],
        memories=[{"memory_type": m.memory_type, "key": m.key, "value": m.value} for m in memories],
        approvals=[
            {
                "id": a.id,
                "action": a.action,
                "action_payload": a.action_payload,
                "status": a.status,
                "resolved_by": a.resolved_by,
            }
            for a in approvals
        ],
        max_steps=max_steps,
    )
