from sqlalchemy import select

from app.agent.orchestrator import AgentOrchestrator
from app.db.models.entities import AgentRun, AgentStep, Approval, Incident
from app.services.approval_service import resolve_approval


def test_new_orchestrator_resumes_from_persisted_checkpoint(db):
    incident = Incident(title="Payment incident", description="payment-service latency increased after latest deployment", severity="SEV2", status="OPEN")
    db.add(incident)
    db.flush()
    run = AgentRun(incident_id=incident.id, status="QUEUED", model_name="reliableops-mock-v1")
    db.add(run)
    db.commit()

    first_worker = AgentOrchestrator()
    paused = first_worker.run(db, run.id)
    assert paused.status == "WAITING_FOR_APPROVAL"
    checkpoint_step = paused.current_step
    approval = db.scalar(select(Approval).where(Approval.run_id == run.id, Approval.status == "PENDING"))
    resolve_approval(db, approval.id, True, "restart-test")

    second_worker = AgentOrchestrator()
    finished = second_worker.run(db, run.id)
    assert finished.status == "COMPLETED"
    assert finished.current_step > checkpoint_step
    numbers = [s.step_number for s in db.scalars(select(AgentStep).where(AgentStep.run_id == run.id)).all()]
    assert len(numbers) == len(set(numbers))
