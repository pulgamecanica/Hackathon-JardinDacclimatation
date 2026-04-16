"""Async media-processing tasks."""
from __future__ import annotations

import structlog
from celery import shared_task

log = structlog.get_logger()


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def summarize_media(self, record_dict: dict):
    """Produce a short text summary for a newly uploaded file."""
    from app.media.processor import summarize
    from app.media.storage import MediaRecord

    record = MediaRecord(**record_dict)
    summary = summarize(record)
    log.info("media_summarized", media_id=record.id, summary=summary)
    return {"media_id": record.id, "summary": summary}
