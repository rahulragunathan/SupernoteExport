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
- **Phase 5 — Output & progress knobs: Done** (PR #4).
  `--page-markers {none,line-break,page-numbers}` (replaces `--page-separators`;
  `page-numbers` emits `## Page N` headers keyed to true source pages via the new
  pure `assemble_transcription`). Per-note progress lines to stderr via a
  `pipeline.run` `on_progress` callback. The `max_pixels` enhancement was
  **investigated and closed as not viable** — the pre-render downscale stays (see
  Resolved).

## Known Issues

None currently. (Reproducible bugs go here; non-bug caveats are under Notes, open
risks under Unknowns.)

## Enhancements

Unscheduled unless a schedule is noted on the item.

- **Front-matter** — optional YAML (source path, capture date, page count, model
  used) for Obsidian Dataview.
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

### PR #4 — page markers, processor pixel cap, progress

Delivered three Enhancement items in one phase:

1. **Per-page structure.** `--page-separators` → `--page-markers {none,line-break,
   page-numbers}`. The joining logic is a pure, unit-tested `assemble_transcription`;
   `page-numbers` headers use the true 1-based source-page index, so a blank page
   leaves a numbering gap rather than renumbering — headers stay aligned to the PDF.
2. **`max_pixels` control — tried, reverted, closed.** First swapped the pre-render
   LANCZOS downscale for the model processor's own `max_pixels` (native images +
   `load(max_pixels=...)`). The `vlm` eval passed, but that was **false confidence**:
   the cliff is intermittent, and `load(max_pixels=...)` was silently ignored —
   mlx-vlm rebuilds the image processor from `preprocessor_config.json` and discards
   the kwarg, so the effective cap stayed at the model default (16.7M). A real note
   (`This Ship`) then produced an empty (embed-only) `.md`. Root-caused by
   instrumenting the boundary (processor `max_pixels` = 16,777,216, not 1.5M).
   **Reverted to the model-agnostic pre-render downscale.** Also investigated deriving
   the cap from model metadata (the ask behind "native support"): not viable — the
   safe point is *below* everything the model advertises. Sweep on the failing note:
   1.5M ✓, 2.0M ✗, 2.36M (`num_position_embeddings × (patch·merge)²`) ✗, 16.7M
   (`size.longest_edge`) ✗. So the 1.5M default is a **hard-coded conservative
   constant** by necessity, with `--max-pixels` as the per-model override. Added a
   deterministic `note_to_page_images` cap test as the primary regression guard (the
   `vlm` eval alone can pass intermittently). The eval's anchor match was also made
   case-insensitive to tolerate capitalization drift.
3. **Progress output.** `pipeline.run` gained an `on_progress(index, total, path,
   status)` callback (status `convert`/`skip`); the CLI prints a per-note stderr
   line. The library stays print-free and unit-tested.

### Runtime validation (2026-07-17)

- **Transcription accuracy on real handwriting.** The first real-folder conversion
  ran clean — the default Qwen3-VL-30B handled the actual notes well, no issues.
  Retires the core "does the default model work on real handwriting" risk (it was the
  main open question). Fallbacks stay documented (`olmOCR-7B`, `Qwen2.5-VL-7B`); wider
  corpus coverage accrues with continued use.

## Unknowns

Least-confident areas and open risks.

- **mlx-vlm API stability.** `generate`/`apply_chat_template` signatures were pinned
  against installed 0.6.5. A future upgrade could shift them; the transcriber is small
  and isolated, so a break is contained to `transcribe.py`. (We do **not** rely on
  `load(**kwargs)` forwarding processor args — PR #4 found that path silently discards
  `max_pixels`, which is why the pixel cap is a pre-render downscale in `convert.py`.)
- **The 1.5M pixel cap is empirical and default-model-specific.** It guards the
  Qwen3-VL empty-generation cliff and can't be derived from model metadata (PR #4).
  A different `--model` may have a different safe ceiling; there's no runtime check
  that the chosen cap is safe for the chosen model — the `vlm` eval covers only the
  default model, and only when cached. Silent empty output on an untested model+cap
  combination remains possible; `--max-pixels` is the manual lever.
- **`_default_hf_home()` assumes `Path.home()` resolves.** Raises `RuntimeError` if
  the home directory can't be determined (no `HOME`, some CI sandboxes). Acceptable
  for a local CLI on macOS; would need a guard if run in a container.

## Notes

- Reading `.note` files from a cloud-synced folder (Google Drive File Stream,
  iCloud, Dropbox) is slow, since files download on demand. A slow folder run is
  input I/O, not a conversion bug — conversion itself is ~1 s/note.
- Python 3.14 is unsupported (dependency wheels); supported range is 3.10–3.13.
- PySN was considered and not adopted; `supernotelib` covers all conversion needs.
