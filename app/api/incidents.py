from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.entities import Incident
from app.db.session import get_db
from app.schemas.incidents import IncidentCreate, IncidentRead
from app.schemas.runs import AgentRunRead, InvestigateRequest
from app.services.incident_service import create_incident, create_or_get_run
from app.workers.tasks import investigate_run

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post("", response_model=IncidentRead, status_code=status.HTTP_201_CREATED)
def post_incident(payload: IncidentCreate, db: Session = Depends(get_db)):
    return create_incident(db, payload)


@router.get("", response_model=list[IncidentRead])
def list_incidents(db: Session = Depends(get_db)):
    return list(db.scalars(select(Incident).order_by(Incident.created_at.desc())).all())


@router.get("/{incident_id}", response_model=IncidentRead)
def get_incident(incident_id: str, db: Session = Depends(get_db)):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.post("/{incident_id}/investigate", response_model=AgentRunRead, status_code=status.HTTP_202_ACCEPTED)
def investigate_incident(
    incident_id: str,
    payload: InvestigateRequest | None = None,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    try:
        run, created = create_or_get_run(db, incident_id, idempotency_key, (payload or InvestigateRequest()).model_name)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if created:
        investigate_run.delay(run.id)
    db.refresh(run)
    return run
