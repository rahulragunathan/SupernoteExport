"""Integration test for the pipeline: real .note conversion + a fake transcriber.

Converts a committed sample note (``tests/fixtures/``) through real ``supernotelib``
while faking only the ``Transcriber`` — so the conversion boundary is genuinely
exercised without needing a multi-gigabyte model. The fixture ships in the repo, so
the suite runs anywhere with no setup.

The fixture keeps its on-device timestamp name (``20260717_012708.note``) on purpose:
that exercises ``naming.py``'s ``YYYYMMDD_HHMMSS`` → ``YYYY-MM-DD`` conversion. The
assertions below encode the fixture's own properties — its ``2026-07-17`` output stem
and its 3-page count — so they are stable facts about a file the repo owns.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from supernote_export.pipeline import run

SAMPLE_NOTE = Path(__file__).parent / "fixtures" / "20260717_012708.note"
SAMPLE_STEM = "2026-07-17"
SAMPLE_PAGES = 3


class FakeTranscriber:
    """Records the pages it was handed and returns deterministic Markdown."""

    def __init__(self) -> None:
        self.calls: list[int] = []

    def transcribe_pages(self, images: list[Image.Image]) -> str:
        self.calls.append(len(images))
        return "# Fake transcription\n\n- point one"


def test_single_file_produces_pdf_and_md_side_by_side(tmp_path):
    fake = FakeTranscriber()
    summary = run(SAMPLE_NOTE, tmp_path, transcriber=fake)

    assert len(summary.converted) == 1
    assert not summary.failed

    pdf = tmp_path / f"{SAMPLE_STEM}.pdf"
    md = tmp_path / f"{SAMPLE_STEM}.md"
    assert pdf.exists() and md.exists()
    assert pdf.read_bytes()[:5] == b"%PDF-"  # real PDF from supernotelib

    text = md.read_text(encoding="utf-8")
    assert text.startswith("# Fake transcription")
    assert text.endswith(f"![[{SAMPLE_STEM}.pdf]]\n")

    # Transcriber saw the real page images.
    assert fake.calls == [SAMPLE_PAGES]


def test_rerun_skips_existing_unless_overwrite(tmp_path):
    fake = FakeTranscriber()
    run(SAMPLE_NOTE, tmp_path, transcriber=fake)

    second = run(SAMPLE_NOTE, tmp_path, transcriber=fake)
    assert len(second.skipped) == 1
    assert not second.converted

    third = run(SAMPLE_NOTE, tmp_path, transcriber=fake, overwrite=True)
    assert len(third.converted) == 1


def test_on_progress_reports_convert_then_skip_per_note(tmp_path):
    events: list[tuple[int, int, str, str]] = []

    def record(current, total, note_path, status):
        events.append((current, total, note_path.name, status))

    run(SAMPLE_NOTE, tmp_path, transcriber=FakeTranscriber(), on_progress=record)
    assert events == [(1, 1, SAMPLE_NOTE.name, "convert")]

    events.clear()
    run(SAMPLE_NOTE, tmp_path, transcriber=FakeTranscriber(), on_progress=record)
    assert events == [(1, 1, SAMPLE_NOTE.name, "skip")]


def test_no_transcriber_yields_embed_only_markdown(tmp_path):
    summary = run(SAMPLE_NOTE, tmp_path, transcriber=None)
    assert len(summary.converted) == 1
    md = (tmp_path / f"{SAMPLE_STEM}.md").read_text(encoding="utf-8")
    assert md == f"![[{SAMPLE_STEM}.pdf]]\n"
