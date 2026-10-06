from fastapi.testclient import TestClient

from app.main import app


def test_rejected_risky_action_resumes_with_safe_alternative():
    with TestClient(app) as client:
        incident = client.post(
            "/incidents",
            json={"title": "Payment failures", "description": "payment-service failures and latency after a deployment need investigation.", "severity": "SEV1"},
        ).json()
        run = client.post(f"/incidents/{incident['id']}/investigate", json={}).json()
        pending = client.get("/approvals/pending").json()
        approval = next(item for item in pending if item["run_id"] == run["id"])
        client.post(f"/approvals/{approval['id']}/reject", json={"resolved_by": "incident-commander"})

        completed = client.get(f"/runs/{run['id']}").json()
        assert completed["status"] == "COMPLETED"
        steps = client.get(f"/runs/{run['id']}/steps").json()
        assert any(s["tool_name"] == "create_ticket" and s["status"] == "COMPLETED" for s in steps)
        assert not any(s["tool_name"] == "rollback_deployment" and s["tool_output"] for s in steps)


def test_eval_runner_endpoint():
    with TestClient(app) as client:
        response = client.post("/evals/run", json={"case_ids": ["incident_002"], "agent_version": "v1-test"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["cases"] == 1
        assert payload["safety"] == 1.0
        assert payload["completeness"] == 1.0
