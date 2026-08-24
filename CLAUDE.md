# CLAUDE.md — SupernoteExport

Project instructions for this repo. The global standards in `~/.claude/CLAUDE.md`
still apply: venv not conda, TDD, double-quoted paths, and the rest.

## What this is

A local CLI that turns Supernote `.note` files into an Obsidian-ready **PDF** and
**transcribed Markdown** pair, one per note. Everything runs offline on Apple
Silicon.

## Architecture

One job per module, under `src/supernote_export/`:

- `discover.py` — turns `--input`, a file or folder, into sorted
  `(note_path, relative_subdir)` pairs.
- `naming.py` — timestamp stem becomes a date, any other stem is kept. Two passes
  reserve the stems you chose on the device before handing out `-2`/`-3` suffixes.
- `convert.py` — wraps `supernotelib` with `note_to_pdf` and `note_to_page_images`,
  which shrinks pages to `--max-pixels`. Owns `DEFAULT_MAX_PIXELS`.
- `transcribe.py` — the `Transcriber` protocol, `MlxVlmTranscriber`, and the pure
  `assemble_transcription`. Sets no environment variables and imports MLX inside
  its methods.
- `writer.py` — `build_markdown` (transcription on top, embed at the bottom) and
  `write_note_outputs`, which stages both files and renames them into place.
- `pipeline.py` — drives discover → convert → transcribe → write, catches per-note
  failures, returns a `Summary`.
- `cli.py` / `__main__.py` — argparse entry point (`python -m supernote_export`).

Data flow: `.note` → a PDF for the embed, plus page PNGs → model → transcription →
`.md`. The model never reads the PDF. The two paths are independent.

[ARCHITECTURE.md](ARCHITECTURE.md) has the full write-up and the diagram. That
diagram is **generated, not drawn by hand**. Edit
`docs/architecture/build_architecture.py`, re-run it, then run the `drawio` skill's
`validate.py` and `render_png.py`. Never hand-edit the `.drawio` XML or the PNG.

[ROADMAP.md](ROADMAP.md) uses **fixed sections**: **Status** (milestones, with
`Done (PR #N)` for anything merged), **Known Issues** (reproducible bugs only),
**Enhancements** (unscheduled unless the item says otherwise), **Resolved** (closed
issues and end-of-phase findings, grouped by PR), **Unknowns** (open risks), and
**Notes** (caveats that are not bugs). Keep README and ARCHITECTURE to current
state. Reasoning and decisions live here.

## Key invariants — do not break

- **Never set `HF_HOME`, or any environment variable, from library code.** Weights
  belong wherever Hugging Face caches them: `~/.cache/huggingface`, unless the
  *user* exports `HF_HOME`. Forcing a location at module scope was tried and
  removed. It imposed a non-standard cache, and because Hugging Face and MLX read
  the variable at import time, it pushed every import in the module below the
  assignment, which needed `# noqa: E402` throughout. If a weights location is ever
  needed again, it belongs in the user's shell profile, or in a CLI flag applied in
  `cli.py` before anything imports `huggingface_hub`. Never at module scope.
  `tests/test_transcribe.py` guards this with a subprocess import probe.
- **MLX is imported inside `MlxVlmTranscriber` methods**, so `--no-transcribe` and
  the whole test suite run without loading a multi-gigabyte model.
- **Naming is worked out, never looked up.** It must stay reproducible across runs
  so `--overwrite` and skip-on-rerun stay stable, so sort notes before naming and
  never probe the disk. Names come from a **two-pass reserved set**, not a count of
  base names: counting alone was tried and collided, because a note renamed on the
  device to `2025-08-17-2` could claim a name the suffixer would later generate,
  which silently skipped or overwrote the second note.
- **A file that exists must be a file that was written in full.** `pipeline.run`
  skips a note only when both outputs are present, and `write_note_outputs` stages
  each file under a unique temp name and renames it into place. Do not reintroduce
  a direct write to a final path: the skip check trusts that a file on disk is
  whole. Unique temp names matter too, so two runs over one output folder cannot
  clean up each other's work.
- **One bad note must not stop a batch.** `pipeline.run` catches per note.
- **The pixel cap is a pre-render downscale in `convert.py`**, applied before any
  model processor sees the image. That is model-agnostic on purpose — see the
  gotcha below. Do **not** move it into the transcriber using the processor's own
  `max_pixels`. That was tried and failed silently: mlx-vlm rebuilds the image
  processor and discards the argument, and it is Qwen-specific anyway.
- **Page numbering follows the true source page.** `assemble_transcription` keys
  `## Page N` headings to the 1-based source index. Blank pages are dropped but
  their number is used up, so headings stay aligned with the PDF: a gap, never a
  renumber.

## Environment

- Python **3.13**. Not 3.14 — the dependencies have no wheels for it.
- `uv venv --python 3.13 .venv`, then `uv pip install -e .[dev,transcribe]`. uv
  brings its own 3.13 build, so this works whether or not Homebrew's `python@3.13`
  is installed; Homebrew's `python3` may be 3.14, which this project cannot use.
  `python3.13 -m venv .venv` plus `pip install -r requirements-dev.txt` does the
  same thing when a 3.13 interpreter is on PATH.
- `requirements-dev.txt` keeps `-e .[dev,transcribe]` **unquoted**. pip tolerates
  the quotes; uv's requirements parser rejects them.

## Packaging

- **`src/` layout and an editable install are required.** The package lives in
  `src/supernote_export/`, so it is *not* importable from the repo root. Imports,
  and pytest with them, only work after `pip install -e .`. This is deliberate:
  the tests exercise the installed artifact, so a packaging bug fails the suite
  instead of hiding behind a working-directory import.
- **Dependencies live only in `pyproject.toml`.** Version constraints belong in
  `[project]`. The `requirements*.txt` files are thin `-e .` pointers. `mlx-vlm` is
  the optional `[transcribe]` extra, and it is Metal-only, so the base install works
  on any platform — which matches the lazy MLX import.
- The build backend is **hatchling**, and
  `[tool.hatch.build.targets.wheel] packages` points at `src/supernote_export`.
  `python -m build` produces a clean wheel: the package only, no tests, fixture, or
  docs, with the console script and the bundled `LICENSE`.

## Testing

- The deterministic layers are unit- or integration-tested: `naming`, `discover`,
  `writer`, `pipeline`, `convert`, `assemble_transcription`, and the `cli` parser
  and printer. Write the failing test first.
- The `pipeline` integration test converts a **committed sample `.note`**
  (`tests/fixtures/20260717_012708.note`) through real `supernotelib`, faking only
  the `Transcriber`. So the conversion boundary is exercised with no model and no
  setup. The tests assert that fixture's own properties: a `2026-07-17` output stem,
  whose timestamp name also exercises `naming.py`'s date conversion, and its 3-page
  count. If you swap the fixture, update `SAMPLE_STEM` and `SAMPLE_PAGES` in
  `test_pipeline.py` and the `.gitignore` negation.
- The model layer has no unit test, by design. An **opt-in eval** covers it
  (`tests/test_vlm_eval.py`, marked `vlm`, deselected by default through `addopts`
  in `pyproject.toml`). Run it with `pytest -m vlm`. It loads the real model, so it
  *skips* when the model is not cached — the mirror of the fixture test's fail-loud
  behavior, because the model is huge and optional while the fixture is cheap and
  always there. Its assertions are tolerant: output is not empty, plus a few printed
  anchors. That guards the empty-output resolution cliff without pinning exact model
  text.
- Before hand-off: `pytest` green, then `ruff format .` and `ruff check .`. The
  `vlm` eval is separate and manual, not part of that gate.

## Gotchas

- Reading `.note` files from a cloud-synced folder (Google Drive, iCloud, Dropbox)
  can be slow, because files download on demand. Conversion itself takes about a
  second per note, so a slow folder run is usually input I/O, not a bug.
- `supernotelib.PdfConverter.convert(-1, ...)` renders every page and returns
  `bytes`.
- **PySN is deliberately not used.** `supernotelib` covers every conversion need, so
  do not reach for PySN when extending `convert.py`.
- **The pixel cap is load-bearing, not cosmetic.** A native page renders at
  1920×2560, about 4.9M pixels. Above roughly 2M pixels, Qwen3-VL sometimes emits an
  *empty* generation through an immediate EOS, which silently produces embed-only
  `.md` files. `note_to_page_images` downscales with LANCZOS to `--max-pixels`,
  default 1.5M, *before* the model sees anything. Measured on a failing page: safe at
  or below 1.77M, empty at or above 2.0M. Do not raise the default toward 2M.

  The default is a **hard-coded conservative constant, not derived from the model**.
  The cliff is undocumented and sits below every capacity the model advertises:
  `size.longest_edge` is 16.7M and the `num_position_embeddings` math implies 2.36M,
  and both produce empty output. See ROADMAP. The `vlm` eval's non-empty assertion
  is the re-validation gate, but it can pass by luck at oversized caps, so trust the
  deterministic `note_to_page_images` cap test as the primary guard. The archival
  PDF is rendered separately, at full resolution.
