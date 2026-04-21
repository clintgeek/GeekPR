from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "geekpr",
    broker=settings.redis_url,
    backend=settings.redis_url,
    # Explicit task-module imports. Celery's default autodiscover looks for
    # a submodule literally named `tasks` inside each package, which doesn't
    # match this layout (app.tasks.analyze_pr, not app.tasks.tasks). Without
    # this the worker starts with zero registered tasks and rejects every
    # incoming message as "unregistered task type".
    include=["app.tasks.analyze_pr"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    broker_connection_retry_on_startup=True,
)
