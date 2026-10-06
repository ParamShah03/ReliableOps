from fastapi import APIRouter, Depends, Response, status
try:
    from redis import Redis
except ImportError:  # Docker/runtime dependency; keep importable for lightweight tests
    Redis = None
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health(response: Response, db: Session = Depends(get_db)):
    settings = get_settings()
    checks = {"database": False, "redis": False}
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        pass
    try:
        if Redis is not None:
            checks["redis"] = bool(Redis.from_url(settings.redis_url, socket_timeout=1).ping())
    except Exception:
        pass
    healthy = all(checks.values())
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ok" if healthy else "degraded", "checks": checks}
