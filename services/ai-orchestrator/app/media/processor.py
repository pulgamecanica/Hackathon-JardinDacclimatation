"""Media processing stubs.

True multimodal inference (vision, ASR) is out of scope for this build:
deploying a vision-capable model (Llama-3.2-Vision or similar) is a
separate infra task. These stubs produce short text summaries so the
agents can reference the media in context.

Replace with real pipelines when a multimodal deployment is available.
"""
from __future__ import annotations

from pathlib import Path

from app.media.storage import MediaRecord


def summarize(record: MediaRecord) -> str:
    kind = record.mime_type.split("/")[0]
    base = Path(record.path).name

    if kind == "image":
        try:
            from PIL import Image

            with Image.open(record.path) as img:
                w, h = img.size
                return f"image {base}: {w}x{h} ({record.mime_type})"
        except Exception as e:  # pragma: no cover - PIL optional
            return f"image {base} ({record.mime_type}); preview unavailable ({e})"

    if kind == "audio":
        return f"audio {base} ({record.mime_type}, {record.size_bytes} bytes); ASR stubbed"

    if kind == "video":
        return f"video {base} ({record.mime_type}, {record.size_bytes} bytes); vision stubbed"

    return f"file {base} ({record.mime_type}, {record.size_bytes} bytes)"
