from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.approvals import ApprovalRead, ApprovalResolution
from app.services.approval_service import pending_approvals, resolve_approval
from app.workers.tasks import investigate_run

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("/pending", response_model=list[ApprovalRead])
def get_pending_approvals(db: Session = Depends(get_db)):
    return pending_approvals(db)


def _resolve(approval_id: str, payload: ApprovalResolution, approve: bool, db: Session):
    try:
        approval = resolve_approval(db, approval_id, approve=approve, resolved_by=payload.resolved_by)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    investigate_run.delay(approval.run_id)
    return approval


@router.post("/{approval_id}/approve", response_model=ApprovalRead)
def approve(approval_id: str, payload: ApprovalResolution, db: Session = Depends(get_db)):
    return _resolve(approval_id, payload, True, db)


@router.post("/{approval_id}/reject", response_model=ApprovalRead)
def reject(approval_id: str, payload: ApprovalResolution, db: Session = Depends(get_db)):
    return _resolve(approval_id, payload, False, db)
