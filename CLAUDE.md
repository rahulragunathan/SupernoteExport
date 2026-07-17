# CLAUDE.md — SupernoteExport

Project instructions for working in this repo. Global standards in
`~/.claude/CLAUDE.md` still apply (venv not conda, TDD, double-quoted paths, etc.).

## What this is

A local CLI that converts Supernote `.note` files into an Obsidian-ready **PDF** +
**transcribed Markdown** pair, one per note. Everything runs offline on Apple Silicon.

## Architecture (single-responsibility modules under `src/supernote_export/`)

- `discover.py` — `--input` (file/folder) → sorted `(note_path, relative_subdir)`.
- `naming.py` — timestamp→date vs. verbatim stem; deterministic `-2/-3` collision suffixing.
- `convert.py` — `supernotelib` wrapper: `note_to_pdf` + `note_to_page_images`.
- `transcribe.py` — `Transcriber` protocol + `MlxVlmTranscriber` (MLX-VLM). Sets
  `HF_HOME` at import; imports MLX lazily inside methods.
- `writer.py` — `build_markdown` (transcription on top, embed at bottom) + `write_note_outputs`.
- `pipeline.py` — orchestrates discover → convert → transcribe → write; per-note
  try/except; returns a `Summary`.
- `cli.py` / `__main__.py` — argparse entrypoint (`python -m supernote_export`).

Data flow: `.note` → (PDF for the embed) + (page PNGs → VLM → transcription) → `.md`.
The VLM never reads the PDF; the two paths are independent.

[ARCHITECTURE.md](ARCHITECTURE.md) has the full write-up and a diagram. The diagram is
**generated, not hand-drawn** — edit `docs/architecture/build_architecture.py` and re-run
it (then the `drawio` skill's `validate.py` + `render_png.py`); never hand-edit the
`.drawio` XML or the PNG.

## Key invariants — do not break

- **`HF_HOME` is set before any HF/mlx import.** Model weights go to `HF_HOME`
  (default `~/Local-Models` via `_default_hf_home()`), set at the top of
  `transcribe.py`. Keep that ordering — those libraries read the variable at
  import time, so only stdlib imports may precede the `os.environ.setdefault`
  call.
- **MLX is imported lazily** (inside `MlxVlmTranscriber` methods) so `--no-transcribe`
  and the whole test suite run without loading a multi-GB model.
- **Naming is deterministic and filesystem-independent** — reproducible across runs
  so `--overwrite` and skip-on-rerun stay stable. Sort notes before naming.
- **One bad note must not abort a batch** — `pipeline.run` catches per-note.

## Environment

- Python **3.13** (homebrew `/opt/homebrew/bin/python3.13`). Not 3.14 — deps lack wheels.
- `python3.13 -m venv .venv` → `pip install -r requirements-dev.txt` (which is just
  `-e ".[dev,transcribe]"`).

## Packaging

- **`src/` layout + editable install required.** The package lives in
  `src/supernote_export/`, so it is *not* importable from the repo root — you must
  `pip install -e .` for imports (and `pytest`) to work. This is deliberate: tests
  exercise the installed artifact, so a packaging bug fails the suite instead of
  hiding behind a working-dir import.
- **Dependencies are single-sourced in `pyproject.toml`.** Version constraints live
  only in `[project]`; `requirements*.txt` are thin `-e .` / `-e ".[dev,transcribe]"`
  pointers. `mlx-vlm` is the optional `[transcribe]` extra (Metal-only), so the base
  install is platform-independent — matching the lazy MLX import.
- Build backend is **hatchling**; `[tool.hatch.build.targets.wheel] packages` points
  at `src/supernote_export`. `python -m build` produces a clean wheel (package only —
  no tests, fixture, or docs) with the console script and bundled `LICENSE`.

## Testing

- Deterministic layers (`naming`, `discover`, `writer`, `pipeline`) are unit/integration
  tested. Write a failing test first (TDD).
- The `pipeline` integration test converts a **committed sample `.note`**
  (`tests/fixtures/20260717_012708.note`) through real `supernotelib`, faking only the
  `Transcriber` — so the conversion boundary is exercised with no model and no setup. The
  tests assert that fixture's properties: a `2026-07-17` output stem (its timestamp name
  exercises `naming.py`'s date conversion) and its 3-page count. If you swap the fixture,
  update `SAMPLE_STEM`/`SAMPLE_PAGES` in `test_pipeline.py` and the `.gitignore` negation.
- The VLM layer has no unit test by design. It's covered by an **opt-in eval**
  (`tests/test_vlm_eval.py`, marked `vlm`, deselected by default via `addopts` in
  pyproject.toml). Run it with `pytest -m vlm`; it loads the real model, so it
  *skips* when the model isn't cached — the mirror of the fixture test's fail-loud,
  since the model is huge and optional while the fixture is cheap and guaranteed.
  Assertions are tolerant (non-empty + a few printed anchors), guarding the empty-
  output resolution cliff without pinning exact VLM text.
- Before hand-off: `pytest` green, `ruff format .`, `ruff check .`. (The `vlm` eval
  is separate and manual — not part of the default gate.)

## Gotchas

- Reading `.note` files from a cloud-synced folder (Google Drive File Stream, iCloud,
  Dropbox) can be slow, since files download on demand. Conversion itself is ~1 s/note,
  so a slow folder run is usually input I/O, not a bug.
- `supernotelib.PdfConverter.convert(-1, ...)` renders all pages and returns `bytes`.
- **PySN is intentionally not used** — `supernotelib` covers all conversion needs, so
  don't reach for PySN when extending `convert.py`.
- **VLM image cap is load-bearing, not cosmetic.** Native page render is 1920×2560
  (~4.9M px). Above ~2M px, Qwen3-VL intermittently emits an *empty* generation
  (immediate EOS) — this silently produced embed-only `.md` files. `note_to_page_images`
  downscales to `--max-pixels` (default 1.5M); measured safe ≤1.77M, broken ≥2.76M. Do
  not raise the default near 2M. The archival PDF is rendered separately at full res.
