from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import ApprovalStatus, RunStatus, StepStatus
from app.db.models.entities import AgentRun, AgentStep, Approval


def pending_approvals(db: Session) -> list[Approval]:
    return list(db.scalars(select(Approval).where(Approval.status == ApprovalStatus.PENDING.value).order_by(Approval.requested_at)).all())


def resolve_approval(db: Session, approval_id: str, approve: bool, resolved_by: str) -> Approval:
    approval = db.get(Approval, approval_id)
    if not approval:
        raise LookupError("Approval not found")
    if approval.status != ApprovalStatus.PENDING.value:
        raise ValueError("Approval has already been resolved")

    approval.status = ApprovalStatus.APPROVED.value if approve else ApprovalStatus.REJECTED.value
    approval.resolved_at = datetime.now(timezone.utc)
    approval.resolved_by = resolved_by

    run = db.get(AgentRun, approval.run_id)
    step = db.get(AgentStep, approval.step_id)
    if run:
        run.status = RunStatus.QUEUED.value
    if step and not approve:
        step.status = StepStatus.REJECTED.value
        step.error_message = f"Action rejected by {resolved_by}"
    db.commit()
    db.refresh(approval)
    return approval
