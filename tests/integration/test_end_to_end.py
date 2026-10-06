from fastapi.testclient import TestClient

from app.main import app


def test_incident_idempotency_approval_resume_and_trace():
    with TestClient(app) as client:
        incident_response = client.post(
            "/incidents",
            json={
                "title": "Payment latency after deployment",
                "description": "payment-service API latency increased by 40% after the latest deployment at 10:05.",
                "severity": "SEV2",
            },
        )
        assert incident_response.status_code == 201
        incident_id = incident_response.json()["id"]

        headers = {"Idempotency-Key": "demo-payment-001"}
        first = client.post(f"/incidents/{incident_id}/investigate", headers=headers, json={})
        assert first.status_code == 202
        run_id = first.json()["id"]
        assert first.json()["status"] == "WAITING_FOR_APPROVAL"

        duplicate = client.post(f"/incidents/{incident_id}/investigate", headers=headers, json={})
        assert duplicate.json()["id"] == run_id

        pending = client.get("/approvals/pending").json()
        approval = next(item for item in pending if item["run_id"] == run_id)
        assert approval["action"] == "rollback_deployment"
        assert approval["action_payload"]["version"] == "v1.4.2"

        approved = client.post(f"/approvals/{approval['id']}/approve", json={"resolved_by": "integration-test"})
        assert approved.status_code == 200

        run = client.get(f"/runs/{run_id}").json()
        assert run["status"] == "COMPLETED"
        assert "database connection pool exhaustion" in run["final_report"]["root_cause"]

        trace = client.get(f"/runs/{run_id}/trace").json()
        step_numbers = [step["step_number"] for step in trace["steps"]]
        assert step_numbers == sorted(step_numbers)
        assert len(step_numbers) == len(set(step_numbers))
        assert any(a["status"] == "APPROVED" for a in trace["approvals"])

        metrics = client.get(f"/runs/{run_id}/metrics").json()
        assert metrics["tool_calls"] >= 5
        assert metrics["step_count"] >= metrics["tool_calls"]
