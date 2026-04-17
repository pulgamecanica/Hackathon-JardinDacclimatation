"""Celery app — queues only. Persistence lives in postgres, not the broker.

Flower (docker-compose service) reads task events here for monitoring.
"""
from __future__ import annotations

import logging

import structlog
from celery import Celery
from celery.signals import task_failure, task_postrun, task_prerun, worker_ready

from app.config import get_settings
from app.usage.db import init_db

# Route through stdlib logging so BoundLogger + add_logger_name have a
# logger.name attribute (the default PrintLogger does not).
logging.basicConfig(format="%(message)s", level=logging.INFO)

structlog.configure(
    processors=[
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
log = structlog.get_logger()

_settings = get_settings()

app = Celery("pavo-ai")
app.conf.update(
    broker_url=_settings.celery_broker_url,
    result_backend=_settings.celery_result_backend,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    task_time_limit=300,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    result_extended=True,
    worker_send_task_events=True,
    task_send_sent_event=True,
    task_routes={
        "app.tasks.inference.*": {"queue": "ai-tasks"},
        "app.tasks.media.*": {"queue": "media"},
    },
    task_default_retry_delay=60,
    task_max_retries=3,
    imports=("app.tasks.inference", "app.tasks.media"),
)


@worker_ready.connect
def _on_worker_ready(**_):
    # Ensure ai_usage_logs exists before tasks run — FastAPI may not be up.
    init_db()


@task_prerun.connect
def _prerun(task_id, task, args, kwargs, **_):
    log.info("task_started", task_id=task_id, task=task.name)


@task_postrun.connect
def _postrun(task_id, task, state, **_):
    log.info("task_completed", task_id=task_id, task=task.name, state=state)


@task_failure.connect
def _failure(task_id, exception, **_):
    log.error("task_failed", task_id=task_id, error=str(exception))


@app.task(bind=True)
def debug_task(self):
    return f"celery ok: {self.request.id}"
