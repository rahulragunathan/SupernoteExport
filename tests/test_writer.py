import os

import pytest

from supernote_export import writer
from supernote_export.writer import build_markdown, write_note_outputs


def test_build_markdown_transcription_on_top_embed_on_bottom():
    md = build_markdown("# Heading\n\n- a point", "2025-08-17.pdf")
    assert md == "# Heading\n\n- a point\n\n![[2025-08-17.pdf]]\n"


def test_build_markdown_without_transcription_is_embed_only():
    md = build_markdown("", "2025-08-17.pdf")
    assert md == "![[2025-08-17.pdf]]\n"


def test_build_markdown_strips_trailing_whitespace_from_transcription():
    md = build_markdown("text\n\n\n", "n.pdf")
    assert md == "text\n\n![[n.pdf]]\n"


def test_write_note_outputs_creates_dir_and_both_files(tmp_path):
    out_dir = tmp_path / "Comedy" / "Level 2"
    pdf_path, md_path = write_note_outputs(
        out_dir, "2025-08-17", b"%PDF-1.4 fake", "body\n\n![[2025-08-17.pdf]]\n"
    )
    assert pdf_path == out_dir / "2025-08-17.pdf"
    assert md_path == out_dir / "2025-08-17.md"
    assert pdf_path.read_bytes() == b"%PDF-1.4 fake"
    assert md_path.read_text(encoding="utf-8") == "body\n\n![[2025-08-17.pdf]]\n"


def test_unencodable_markdown_publishes_nothing(tmp_path):
    # A lone surrogate cannot be encoded as UTF-8. It fails during staging,
    # with no mocking. Neither final file may appear.
    with pytest.raises(UnicodeEncodeError):
        write_note_outputs(tmp_path, "2025-08-17", b"%PDF-1.4 fake", "notes \ud800")

    assert list(tmp_path.iterdir()) == []


def test_failure_while_publishing_leaves_the_previous_pair_intact(tmp_path, monkeypatch):
    write_note_outputs(tmp_path, "2025-08-17", b"%PDF-1.4 first", "first\n")
    real_replace = os.replace

    def failing_replace(src, dst):
        if str(dst).endswith(".md"):
            raise OSError("simulated failure publishing the markdown")
        return real_replace(src, dst)

    monkeypatch.setattr(writer.os, "replace", failing_replace)
    with pytest.raises(OSError):
        write_note_outputs(tmp_path, "2025-08-17", b"%PDF-1.4 second", "second\n")

    assert (tmp_path / "2025-08-17.md").read_text(encoding="utf-8") == "first\n"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["2025-08-17.md", "2025-08-17.pdf"]


def test_successful_write_leaves_no_temp_files_behind(tmp_path):
    write_note_outputs(tmp_path, "2025-08-17", b"%PDF-1.4 fake", "# Notes\n")

    assert sorted(p.name for p in tmp_path.iterdir()) == ["2025-08-17.md", "2025-08-17.pdf"]
