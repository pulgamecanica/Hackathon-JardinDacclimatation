"""Disk-backed media storage.

Uploads are saved under a per-session directory. The disk layout is:

  <media_root>/<session_id>/<media_id>_<sanitized_filename>

`save_upload` returns a `MediaRecord` describing the file. True multi-
modal inference is out of scope for this build — `process_media` runs a
lightweight description pass (see app.media.processor).
"""
from __future__ import annotations

import mimetypes
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import uuid4

from app.config import get_settings

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize(name: str) -> str:
    cleaned = _SAFE_NAME.sub("_", name).strip("._") or "upload"
    return cleaned[:120]


@dataclass
class MediaRecord:
    id: str
    session_id: str
    path: str
    mime_type: str
    size_bytes: int
    original_name: str

    def to_dict(self) -> dict:
        return asdict(self)


def save_upload(*, session_id: str, filename: str, data: bytes) -> MediaRecord:
    root = Path(get_settings().media_root) / session_id
    root.mkdir(parents=True, exist_ok=True)

    media_id = str(uuid4())
    safe = _sanitize(filename)
    target = root / f"{media_id}_{safe}"
    target.write_bytes(data)

    mime = mimetypes.guess_type(safe)[0] or "application/octet-stream"
    return MediaRecord(
        id=media_id,
        session_id=session_id,
        path=str(target),
        mime_type=mime,
        size_bytes=len(data),
        original_name=filename,
    )
