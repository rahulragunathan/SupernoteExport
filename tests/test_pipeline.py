"""Integration test for the pipeline: real .note conversion + a fake transcriber.

Uses a real sample note (read-only) so the ``supernotelib`` path is genuinely
exercised. Skips if the sample is unavailable, keeping the suite runnable
anywhere without shipping personal notes in the repo.
"""

from pathlib import Path

import pytest

from PIL import Image

from supernote_sync.pipeline import run

SAMPLE_NOTE = Path(
    "/Users/rahulragunathan/Library/CloudStorage/GoogleDrive-rahul.ragunathan@gmail.com"
    "/My Drive/Supernote/Note/Improv/Friendo/Level 2/20250817_132236.note"
)

needs_sample = pytest.mark.skipif(not SAMPLE_NOTE.exists(), reason="sample .note not present")


class FakeTranscriber:
    """Records the pages it was handed and returns deterministic Markdown."""

    def __init__(self) -> None:
        self.calls: list[int] = []

    def transcribe_pages(self, images: list[Image.Image]) -> str:
        self.calls.append(len(images))
        return "# Fake transcription\n\n- point one"


@needs_sample
def test_single_file_produces_pdf_and_md_side_by_side(tmp_path):
    fake = FakeTranscriber()
    summary = run(SAMPLE_NOTE, tmp_path, transcriber=fake)

    assert len(summary.converted) == 1
    assert not summary.failed

    pdf = tmp_path / "2025-08-17.pdf"
    md = tmp_path / "2025-08-17.md"
    assert pdf.exists() and md.exists()
    assert pdf.read_bytes()[:5] == b"%PDF-"  # real PDF from supernotelib

    text = md.read_text(encoding="utf-8")
    assert text.startswith("# Fake transcription")
    assert text.endswith("![[2025-08-17.pdf]]\n")

    # Transcriber saw the real page images (this note has 3 pages).
    assert fake.calls == [3]


@needs_sample
def test_rerun_skips_existing_unless_overwrite(tmp_path):
    fake = FakeTranscriber()
    run(SAMPLE_NOTE, tmp_path, transcriber=fake)

    second = run(SAMPLE_NOTE, tmp_path, transcriber=fake)
    assert len(second.skipped) == 1
    assert not second.converted

    third = run(SAMPLE_NOTE, tmp_path, transcriber=fake, overwrite=True)
    assert len(third.converted) == 1


@needs_sample
def test_no_transcriber_yields_embed_only_markdown(tmp_path):
    summary = run(SAMPLE_NOTE, tmp_path, transcriber=None)
    assert len(summary.converted) == 1
    md = (tmp_path / "2025-08-17.md").read_text(encoding="utf-8")
    assert md == "![[2025-08-17.pdf]]\n"
