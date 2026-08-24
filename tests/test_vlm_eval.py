"""Opt-in eval: real MLX-VLM transcription of the committed fixture.

This is an *eval*, not a unit test. It's deselected by default (see `addopts` in
pyproject.toml); run it explicitly with:

    pytest -m vlm

Two choices set it apart from the `supernotelib` integration test in
``test_pipeline.py``:

- **It skips when the model is not cached, instead of failing.** The fixture is
  cheap and always there, so its test fails loudly when it goes missing. The model
  is large and optional, so its eval skips when absent. Fail or skip tracks whether
  the dependency is cheap and guaranteed, or expensive and optional.
- **It asserts tolerant properties, not an exact transcription.** Model output
  drifts between model and mlx-vlm versions, so a golden file would be flaky
  forever. The real job is to catch the image-resolution cliff (see ROADMAP): above
  about 2M pixels the model silently returns an empty generation, which showed up as
  embed-only `.md` files. This eval runs the full pipeline — real render, real pixel
  cap, real model — and checks that the output is not empty and carries a few
  clearly printed anchors. That is exactly the signal such a regression erases.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from supernote_export.pipeline import run
from supernote_export.transcribe import DEFAULT_MODEL, MlxVlmTranscriber

pytestmark = pytest.mark.vlm

SAMPLE_NOTE = Path(__file__).parent / "fixtures" / "20260717_012708.note"
SAMPLE_STEM = "2026-07-17"

# Clearly-printed words from pages 1-2, stable across model versions. Matched
# case-insensitively (see below): the anchors' *presence* is the signal, while
# capitalization of ambiguous handwriting is drift the eval should tolerate.
# Deliberately excludes the sloppy-handwriting line and layout-dependent bits (the
# table, columns), which are exactly what *should* be allowed to drift.
EXPECTED_ANCHORS = [
    "Introduction",  # page 1 heading
    "Magna Carta",  # page 1 numbered list
    "Declaration of Independence",  # page 1 numbered list
    "Green Peppers",  # page 2 toppings
    "Black Olives",  # page 2 toppings
]


def _require_cached_model() -> None:
    """Skip unless the model is loadable offline — never trigger a download.

    Gates on ``config.json`` being in the local HF cache (``~/.cache/huggingface``
    unless the user exports ``HF_HOME``; this repo never sets it — see CLAUDE.md).
    ``try_to_load_from_cache`` returns the file's path as a ``str`` when cached, or
    a non-``str`` sentinel otherwise, without any network.

    We deliberately do *not* use ``snapshot_download(local_files_only=True)``: it
    demands every file in the repo, so a model that ``mlx_vlm`` loaded fine — but
    that never pulled non-essential files like ``.gitattributes``/``README.md`` —
    is wrongly reported as uncached. ``config.json`` is what ``transcribe`` actually
    reads, so its presence is the honest "can this load offline?" signal.
    """
    from huggingface_hub import try_to_load_from_cache

    if not isinstance(try_to_load_from_cache(DEFAULT_MODEL, "config.json"), str):
        pytest.skip(f"{DEFAULT_MODEL} not cached locally (run once to download it)")


def test_vlm_transcription_is_nonempty_and_carries_expected_content(tmp_path):
    _require_cached_model()

    summary = run(SAMPLE_NOTE, tmp_path, transcriber=MlxVlmTranscriber())
    assert len(summary.converted) == 1
    assert not summary.failed

    md = (tmp_path / f"{SAMPLE_STEM}.md").read_text(encoding="utf-8")

    # Embed-only output is the exact signature of the resolution-cliff regression.
    assert md.strip() != f"![[{SAMPLE_STEM}.pdf]]", (
        "transcription was empty (embed-only .md) — the image-resolution cliff"
    )

    lowered = md.lower()  # tolerate capitalization drift on ambiguous handwriting
    missing = [anchor for anchor in EXPECTED_ANCHORS if anchor.lower() not in lowered]
    assert not missing, f"transcription is missing clearly-printed content: {missing}"
