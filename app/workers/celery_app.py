try:
    from celery import Celery
except ImportError:  # lightweight eager fallback for environments without Celery installed
    class _EagerTask:
        def __init__(self, fn, bind=False):
            self.fn = fn
            self.bind = bind

        def delay(self, *args, **kwargs):
            return self.run(*args, **kwargs)

        def run(self, *args, **kwargs):
            if self.bind:
                return self.fn(None, *args, **kwargs)
            return self.fn(*args, **kwargs)

    class _Conf(dict):
        def update(self, **kwargs):
            super().update(kwargs)

    class Celery:
        def __init__(self, *args, **kwargs):
            self.conf = _Conf()

        def task(self, *dargs, **dkwargs):
            def decorator(fn):
                return _EagerTask(fn, bind=dkwargs.get("bind", False))
            return decorator

        def autodiscover_tasks(self, *args, **kwargs):
            return None

from app.core.config import get_settings

settings = get_settings()
celery_app = Celery("reliableops", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=True,
    timezone="UTC",
)
celery_app.autodiscover_tasks(["app.workers"])
