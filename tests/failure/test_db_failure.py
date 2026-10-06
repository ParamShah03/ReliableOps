import pytest
from sqlalchemy.exc import OperationalError

import app.workers.tasks as tasks


class FakeDB:
    def close(self):
        pass


def test_worker_does_not_swallow_database_failure(monkeypatch):
    monkeypatch.setattr(tasks, "SessionLocal", lambda: FakeDB())

    def fail_run(self, db, run_id):
        raise OperationalError("checkpoint failed", {}, Exception("db unavailable"))

    monkeypatch.setattr(tasks.AgentOrchestrator, "run", fail_run)
    with pytest.raises(OperationalError):
        tasks.investigate_run.run("run-db-failure")
