# ROADMAP — SupernoteExport

Fixed sections, maintained going forward: **Status**, **Known Issues**,
**Enhancements**, **Resolved**, **Unknowns**, **Notes**.

## Status

Milestones and their completion; PR reference for anything Done.

- **Phase 1 — Ad-hoc conversion pipeline: Done** (baseline, `75e455e`).
  `.note` → PDF + transcribed Markdown, one pair per note, local MLX-VLM
  transcription, mirrored subfolder output.
- **Phase 2 — Post-rename cleanup: Done** (PR #1).
  Repo renamed `SupernoteSync` → `SupernoteExport`; package renamed to match
  (`supernote_export`); machine-specific hardcoding removed (`HF_HOME` default via
  `Path.home()`, test path via `SUPERNOTE_TEST_NOTE`); `ARCHITECTURE.md` added with
  a generated diagram.
- **Phase 3 — Committed test fixture + VLM eval: Done** (PR #2).
  A disposable sample note (`tests/fixtures/20260717_012708.note`) is committed and
  the integration tests point at it directly; `SUPERNOTE_TEST_NOTE` removed. Added
  an opt-in VLM eval (`pytest -m vlm`, deselected by default) that runs the real
  model end-to-end and asserts tolerant properties.
- **Phase 4 — Packaging + MIT license: Done** (PR #3).
  `src/` layout; hatchling `[build-system]`; single-sourced dependencies
  (`requirements*.txt` as thin `-e .` pointers); `[transcribe]` extra gating the
  Metal-only `mlx-vlm`; `supernote-export` console script; MIT `LICENSE`.
  `pip install "git+https://…"` works; `python -m build` produces a clean
  package-only wheel.

## Known Issues

None currently. (Reproducible bugs go here; non-bug caveats are under Notes, open
risks under Unknowns.)

## Enhancements

Unscheduled unless a schedule is noted on the item.

- **Per-page structure in the `.md`** — optional page headers/markers instead of a
  bare `---` separator, if page-addressable notes are wanted.
- **`max_pixels` control** — expose the VLM processor's pixel cap for small-text
  pages, a more effective knob than post-render upscaling.
- **Front-matter** — optional YAML (source path, capture date, page count, model
  used) for Obsidian Dataview.
- **Progress output** — per-note progress line during long batches (currently only a
  final summary).
- **Watch/auto-sync mode** — deferred by design; invocation stays ad-hoc.
- **Model comparison harness** — quick side-by-side of the shortlisted models on a
  handful of real pages, to pick empirically if the default disappoints.

## Resolved

Closed issues and end-of-phase review findings, by PR.

### Phase 1 (baseline)

- **VLM image-resolution cliff.** First real batch produced empty transcriptions
  for 5/7 notes. Root-caused to image resolution: a measured scale sweep on a
  failing page showed reliable, *deterministic* output at ≤1.77M px and consistent
  **empty** output at ≥2.76M px (native ~4.9M). `note_to_page_images` now caps at
  `--max-pixels` (default 1.5M). Replaced the old `--image-scale` multiplier, which
  was the wrong lever.

### PR #1 — post-rename cleanup

`/code-review high` over the branch; every finding was documentation drift
introduced by the phase itself, not a logic defect. All fixed in-branch:

1. `CLAUDE.md` claimed the integration test "skips if absent" — corrected to
   fail-loud.
2. `ROADMAP.md` carried a stale, hand-maintained test count — the number was removed
   rather than reset (it had drifted twice). Watch for the same pattern in other
   hand-maintained figures.
3. `build_architecture.py` re-found its own `<diagram>` element instead of using the
   variable two lines above — refactored; generated `.drawio` verified
   byte-identical.
4. `CLAUDE.md` didn't mention `ARCHITECTURE.md` or that the diagram is generated —
   added.

### PR #2 — committed fixture

- **`SUPERNOTE_TEST_NOTE` weak contract.** The env var read as "point at any note"
  but the tests assert one sample's stem and page count, so any other note failed
  with a confusing assertion error. Replaced by a committed fixture the tests point
  at directly — the assertions now describe a file the repo owns, and no setup is
  needed.

### Runtime validation (2026-07-17)

- **Transcription accuracy on real handwriting.** The first real-folder conversion
  ran clean — the default Qwen3-VL-30B handled the actual notes well, no issues.
  Retires the core "does the default model work on real handwriting" risk (it was the
  main open question). Fallbacks stay documented (`olmOCR-7B`, `Qwen2.5-VL-7B`); wider
  corpus coverage accrues with continued use.

## Unknowns

Least-confident areas and open risks.

- **mlx-vlm API stability.** `generate`/`apply_chat_template` signatures were pinned
  against installed 0.6.5. A future upgrade could shift them; the transcriber is
  small and isolated, so a break is contained to `transcribe.py`.
- **`_default_hf_home()` assumes `Path.home()` resolves.** Raises `RuntimeError` if
  the home directory can't be determined (no `HOME`, some CI sandboxes). Acceptable
  for a local CLI on macOS; would need a guard if run in a container.

## Notes

- Reading `.note` files from a cloud-synced folder (Google Drive File Stream,
  iCloud, Dropbox) is slow, since files download on demand. A slow folder run is
  input I/O, not a conversion bug — conversion itself is ~1 s/note.
- Python 3.14 is unsupported (dependency wheels); supported range is 3.10–3.13.
- PySN was considered and not adopted; `supernotelib` covers all conversion needs.
