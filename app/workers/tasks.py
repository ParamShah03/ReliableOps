import logging

from app.agent.orchestrator import AgentOrchestrator
from app.db.session import SessionLocal
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="reliableops.investigate_run", autoretry_for=(), max_retries=0)
def investigate_run(self, run_id: str) -> dict:
    db = SessionLocal()
    try:
        run = AgentOrchestrator().run(db, run_id)
        return {"run_id": run.id, "status": run.status, "current_step": run.current_step}
    except Exception:
        logger.exception("Investigation worker crashed for run %s", run_id)
        raise
    finally:
        db.close()
