from app.agent.orchestrator import AgentOrchestrator
from app.db.models.entities import AgentRun, Incident


def test_max_step_limit_stops_agent(db):
    incident = Incident(title="Payment latency", description="payment-service latency increased after deployment", severity="SEV2", status="OPEN")
    db.add(incident)
    db.flush()
    run = AgentRun(incident_id=incident.id, status="QUEUED", model_name="reliableops-mock-v1")
    db.add(run)
    db.commit()

    orchestrator = AgentOrchestrator()
    original = orchestrator.settings.max_agent_steps
    orchestrator.settings.max_agent_steps = 1
    try:
        result = orchestrator.run(db, run.id)
        assert result.status == "MAX_STEPS_EXCEEDED"
        assert result.current_step == 1
    finally:
        orchestrator.settings.max_agent_steps = original
