from app.media.processor import summarize
from app.media.storage import save_upload


def test_save_upload_writes_file():
    rec = save_upload(session_id="abc", filename="my photo.jpg", data=b"\xff\xd8\xff\xd9")
    assert rec.session_id == "abc"
    assert rec.mime_type == "image/jpeg"
    assert rec.size_bytes == 4
    assert " " not in rec.path


def test_summarize_handles_unknown_kind(tmp_path):
    from app.media.storage import MediaRecord

    f = tmp_path / "notes.txt"
    f.write_text("hello")
    rec = MediaRecord(
        id="1", session_id="s", path=str(f),
        mime_type="text/plain", size_bytes=5, original_name="notes.txt",
    )
    summary = summarize(rec)
    assert "notes.txt" in summary
