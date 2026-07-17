# CLAUDE.md — SupernoteSync

Project instructions for working in this repo. Global standards in
`~/.claude/CLAUDE.md` still apply (venv not conda, TDD, double-quoted paths, etc.).

## What this is

A local CLI that converts Supernote `.note` files into an Obsidian-ready **PDF** +
**transcribed Markdown** pair, one per note. Everything runs offline on Apple Silicon.

## Architecture (single-responsibility modules under `supernote_sync/`)

- `discover.py` — `--input` (file/folder) → sorted `(note_path, relative_subdir)`.
- `naming.py` — timestamp→date vs. verbatim stem; deterministic `-2/-3` collision suffixing.
- `convert.py` — `supernotelib` wrapper: `note_to_pdf` + `note_to_page_images`.
- `transcribe.py` — `Transcriber` protocol + `MlxVlmTranscriber` (MLX-VLM). Sets
  `HF_HOME` at import; imports MLX lazily inside methods.
- `writer.py` — `build_markdown` (transcription on top, embed at bottom) + `write_note_outputs`.
- `pipeline.py` — orchestrates discover → convert → transcribe → write; per-note
  try/except; returns a `Summary`.
- `cli.py` / `__main__.py` — argparse entrypoint (`python -m supernote_sync`).

Data flow: `.note` → (PDF for the embed) + (page PNGs → VLM → transcription) → `.md`.
The VLM never reads the PDF; the two paths are independent.

## Key invariants — do not break

- **Model weights never touch Google Drive or the Vault.** They go to `HF_HOME`
  (default `/Users/rahulragunathan/Local-Models`), set at the top of `transcribe.py`
  *before* any HF/mlx import. Keep that ordering.
- **MLX is imported lazily** (inside `MlxVlmTranscriber` methods) so `--no-transcribe`
  and the whole test suite run without loading a multi-GB model.
- **Naming is deterministic and filesystem-independent** — reproducible across runs
  so `--overwrite` and skip-on-rerun stay stable. Sort notes before naming.
- **One bad note must not abort a batch** — `pipeline.run` catches per-note.

## Environment

- Python **3.13** (homebrew `/opt/homebrew/bin/python3.13`). Not 3.14 — deps lack wheels.
- `python3.13 -m venv .venv` → `pip install -r requirements-dev.txt`.

## Testing

- Deterministic layers (`naming`, `discover`, `writer`, `pipeline`) are unit/integration
  tested. Write a failing test first (TDD).
- The `pipeline` integration test uses a **real sample `.note`** (skips if absent) plus a
  **fake `Transcriber`** — so `supernotelib` is exercised for real but no model is needed.
- The VLM layer has no unit test by design; verify by running it and eyeballing output.
- Before hand-off: `pytest` green, `ruff format .`, `ruff check .`.

## Gotchas

- Reading `.note` files from Google Drive File Stream can be slow (on-demand download);
  conversion itself is ~1 s/note. A slow folder run is usually Drive I/O, not a bug.
- `supernotelib.PdfConverter.convert(-1, ...)` renders all pages and returns `bytes`.
- **VLM image cap is load-bearing, not cosmetic.** Native page render is 1920×2560
  (~4.9M px). Above ~2M px, Qwen3-VL intermittently emits an *empty* generation
  (immediate EOS) — this silently produced embed-only `.md` files. `note_to_page_images`
  downscales to `--max-pixels` (default 1.5M); measured safe ≤1.77M, broken ≥2.76M. Do
  not raise the default near 2M. The archival PDF is rendered separately at full res.
