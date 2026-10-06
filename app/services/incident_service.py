from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import IncidentStatus, RunStatus
from app.db.models.entities import AgentRun, IdempotencyKey, Incident
from app.schemas.incidents import IncidentCreate


def create_incident(db: Session, payload: IncidentCreate) -> Incident:
    incident = Incident(
        title=payload.title,
        description=payload.description,
        severity=payload.severity,
        status=IncidentStatus.OPEN.value,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


def create_or_get_run(db: Session, incident_id: str, idempotency_key: str | None, model_name: str | None) -> tuple[AgentRun, bool]:
    incident = db.get(Incident, incident_id)
    if not incident:
        raise LookupError("Incident not found")

    scope = f"investigate:{incident_id}"
    if idempotency_key:
        existing_key = db.scalar(
            select(IdempotencyKey).where(IdempotencyKey.scope == scope, IdempotencyKey.key == idempotency_key)
        )
        if existing_key:
            existing_run = db.get(AgentRun, existing_key.resource_id)
            if existing_run:
                return existing_run, False

    settings = get_settings()
    run = AgentRun(
        incident_id=incident_id,
        status=RunStatus.QUEUED.value,
        model_name=model_name or ("reliableops-mock-v1" if settings.llm_provider == "mock" else settings.llm_model),
    )
    incident.status = IncidentStatus.INVESTIGATING.value
    db.add(run)
    db.flush()
    if idempotency_key:
        db.add(
            IdempotencyKey(
                scope=scope,
                key=idempotency_key,
                resource_type="agent_run",
                resource_id=run.id,
            )
        )
    db.commit()
    db.refresh(run)
    return run, True
