from celery import Celery  # type: ignore[import-untyped]
from celery.signals import (  # type: ignore[import-untyped]
    after_setup_logger,
    after_setup_task_logger,
)

from app.core.config import settings
from app.core.logging import suppress_sensitive_transport_logs

# Celery configures logging after importing this module, so enforce the
# transport policy both now and after each Celery logger setup event.
suppress_sensitive_transport_logs()
after_setup_logger.connect(suppress_sensitive_transport_logs, weak=False)
after_setup_task_logger.connect(suppress_sensitive_transport_logs, weak=False)

celery_app = Celery(
    "postx",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    task_track_started=True,
    result_expires=3600,
)
