"""Integration test for the pipeline: real .note conversion + a fake transcriber.

Uses a real sample note (read-only) so the ``supernotelib`` path is genuinely
exercised. Personal notes aren't shipped in the repo, so the note's location comes
from the ``SUPERNOTE_TEST_NOTE`` environment variable.

The variable is required: an unset or bad path fails the run rather than skipping
it, so this — the only coverage of the real ``supernotelib`` boundary — cannot
disappear silently.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from PIL import Image

from supernote_export.pipeline import run

SAMPLE_NOTE_ENV_VAR = "SUPERNOTE_TEST_NOTE"


@pytest.fixture(scope="session")
def sample_note() -> Path:
    raw = os.environ.get(SAMPLE_NOTE_ENV_VAR, "").strip()
    if not raw:
        pytest.fail(
            f"{SAMPLE_NOTE_ENV_VAR} is not set, so the real-.note integration tests "
            f"cannot run. Point it at a .note file, e.g.\n"
            f"    export {SAMPLE_NOTE_ENV_VAR}='/path/to/20250817_132236.note'\n"
            f"See README > Development."
        )
    path = Path(raw)
    if not path.is_file():
        pytest.fail(f"{SAMPLE_NOTE_ENV_VAR} points at '{path}', which is not a file.")
    return path


class FakeTranscriber:
    """Records the pages it was handed and returns deterministic Markdown."""

    def __init__(self) -> None:
        self.calls: list[int] = []

    def transcribe_pages(self, images: list[Image.Image]) -> str:
        self.calls.append(len(images))
        return "# Fake transcription\n\n- point one"


def test_single_file_produces_pdf_and_md_side_by_side(tmp_path, sample_note):
    fake = FakeTranscriber()
    summary = run(sample_note, tmp_path, transcriber=fake)

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


def test_rerun_skips_existing_unless_overwrite(tmp_path, sample_note):
    fake = FakeTranscriber()
    run(sample_note, tmp_path, transcriber=fake)

    second = run(sample_note, tmp_path, transcriber=fake)
    assert len(second.skipped) == 1
    assert not second.converted

    third = run(sample_note, tmp_path, transcriber=fake, overwrite=True)
    assert len(third.converted) == 1


def test_no_transcriber_yields_embed_only_markdown(tmp_path, sample_note):
    summary = run(sample_note, tmp_path, transcriber=None)
    assert len(summary.converted) == 1
    md = (tmp_path / "2025-08-17.md").read_text(encoding="utf-8")
    assert md == "![[2025-08-17.pdf]]\n"
