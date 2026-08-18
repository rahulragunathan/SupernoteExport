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
- **Phase 5 — Output & progress knobs: Done** (PR #5).
  `--page-markers {none,line-break,page-numbers}` (replaces `--page-separators`;
  `page-numbers` emits `## Page N` headers keyed to true source pages via the new
  pure `assemble_transcription`). Per-note progress lines to stderr via a
  `pipeline.run` `on_progress` callback. The `max_pixels` enhancement was
  **investigated and closed as not viable** — the pre-render downscale stays (see
  Resolved).

- **Phase 6 — Standard Hugging Face cache location: Done** (PR #7).
  `transcribe.py` no longer sets `HF_HOME`; weights go to `~/.cache/huggingface`
  unless the user exports `HF_HOME` themselves. Removes `_default_hf_home()`, the
  module-level `os.environ.setdefault`, and the `# noqa: E402` import ordering it
  required. Guarded by a subprocess import probe in `tests/test_transcribe.py`.

## Known Issues

Found by two reviews: the PR #9 repo review (internal `/code-review high`, Codex,
and Gemini) and a later full-codebase review by GPT-5.6-Sol. Each one was checked
against the code. None has shown up in a real run yet.

- **Names shift between runs.** Each run works out names from the notes it can
  see, so two runs that see different notes hand out different names. Convert one
  note from 17 August today and a second one tomorrow: both are named
  `2025-08-17`, and the tool skips the second without a word. A note that syncs
  down late shifts every suffix in that folder, so older notes get skipped and one
  note is written twice. Reserving names inside a run does not help — PR #<N> does
  exactly that and this still stands. The tool has to remember which note produced
  which file, which needs its own phase.
- **A stray PDF gets overwritten.** If `<name>.pdf` exists in the output folder
  but `<name>.md` does not, the run converts the note and replaces that PDF, even
  without `--overwrite`. A PDF that came from somewhere else is gone.
- **A dropped page looks like a blank page.** The model sometimes returns nothing
  for one page. `assemble_transcription` drops empty pages, so that page vanishes
  from the Markdown. With `--page-markers page-numbers` the gap looks exactly like
  a page that was blank on purpose.
- **A long page is cut off in silence.** `_transcribe_one` stops at 4,096 tokens
  and keeps only the text. `mlx-vlm` reports `finish_reason == "length"` when it
  hits that cap, and we ignore it. A dense page is written out as a finished note.
- **Indentation on a page's first line is stripped.** `assemble_transcription` and
  `_strip_code_fence` both call `strip()`. If a page starts with an indented list
  or block, that indent is lost — the opposite of what the prompt asks the model
  to preserve.
- **Half-loaded transcriber poisons the rest of a batch.** `_ensure_loaded` assigns
  `self._model` before `load_config` runs; if the latter raises (e.g. network error
  on a partially cached model), the per-note catch swallows it and every later note
  skips loading and fails on `_config=None` with an unrelated error. Fix shape: set
  all three attributes only after all loads succeed.
- **`_strip_code_fence` corrupts a transcription that genuinely starts with a code
  block** — it deletes the real opening ` ``` ` and orphans the closing one, turning
  the rest of the page into a code block in Obsidian. Only bites notes whose first
  line is a fenced snippet.
- **Bad `--input` prints a raw traceback.** `discover_notes` raises
  `ValueError`/`FileNotFoundError` outside the per-note try, and `cli.main` has no
  handler — a typo'd path crashes instead of printing a one-line error.
- **Missing `[transcribe]` extra fails late and per-note** *(Gemini)*. A base
  install run without `--no-transcribe` renders every note's PDF, then fails each
  note with `ModuleNotFoundError: mlx_vlm` inside the batch loop. Fix shape:
  pre-flight the import in `cli.py` with a `pip install …[transcribe]` hint.
- **Some filenames break the embed.** `build_markdown` drops the filename straight
  into `![[...]]`. Obsidian reads `[` and `]` as link syntax, `|` as an alias, and
  `#` as a heading link, so a note called `Status #2` or `A|B` points at the wrong
  file or fails to embed.

## Enhancements

Unscheduled unless a schedule is noted on the item.

- **Front-matter** — optional YAML (source path, capture date, page count, model
  used) for Obsidian Dataview.
- **Watch/auto-sync mode** — deferred by design; invocation stays ad-hoc.
- **Model comparison harness** — quick side-by-side of the shortlisted models on a
  handful of real pages, to pick empirically if the default disappoints.

From the 2026-08-10 repo review:

- **Load each notebook once** — `note_to_pdf` and `note_to_page_images` each call
  `sn.load_notebook` on the same file, so every note is read and parsed twice; on
  cloud-synced input (the documented slow path) that doubles the dominant I/O cost.
- **Detect all-empty transcription** *(Codex)* — an empty VLM result on a non-empty
  note is currently written as a normal-looking embed-only `.md` (the resolution-
  cliff signature). Warn or record a distinct per-note outcome; note the inherent
  ambiguity with genuinely blank notes.
- **Validate library-seam options** *(internal + Codex)* — `page_markers` and
  `pdf_mode` are validated only by argparse; passed programmatically, an invalid
  value silently degrades to `none`/raster. Also decide whether `--max-pixels <= 0`
  (currently a silent full-resolution escape hatch, tested behavior) should be
  rejected or documented as an explicit unsafe opt-out.
- **Discovery robustness** *(Gemini + internal)* — filter `rglob` hits with
  `is_file()` (a *directory* named `*.note` currently enters the batch and fails
  per-note) and consider case-insensitive `.NOTE` matching.
- **Test coverage additions** *(Gemini)* — per-note failure recovery (the
  `try/except` in `pipeline.run` is untested), `cli.main` exit codes and summary
  output, and vector `--pdf-mode` (raster is covered via the pipeline test's
  `%PDF-` assertion).
- **Consolidate fixture constants** *(Gemini)* — `SAMPLE_NOTE`/`SAMPLE_STEM`/
  `SAMPLE_PAGES` are duplicated across three test modules; a `tests/conftest.py`
  would single-source them.
- **Packaging metadata alignment** *(Codex + Gemini)* — `requires-python = ">=3.10"`
  has no `<3.14` bound although docs everywhere say 3.14 is unsupported, so pip on
  3.14 will attempt an install that dies on dependency wheels. Also reconsider the
  lone `Operating System :: MacOS` classifier given the base (PDF-only) install is
  cross-platform.
- **Stream pages instead of holding them all** — `note_to_page_images` builds every
  page image before the model sees any of them, and the `list[Image]` protocol
  writes that into the design. An iterator would cut memory on long notebooks and
  pairs well with loading each notebook once.
- **Make the eval's cache check honest** — `_require_cached_model` looks only for
  `config.json`, so a partly cached model can still download gigabytes when you run
  `pytest -m vlm`.

## Resolved

Closed issues and end-of-phase review findings, by PR.

### PR #<N> — output naming and skip integrity

Two of the seven bugs from the PR #9 review. Both came from the pipeline trusting
a signal that did not mean what it assumed.

1. **One run could plan the same name twice.** `plan_output_names` counted base
   names and never reserved the finished ones, so a note renamed on the device to
   `2025-08-17-2` and a date-derived `2025-08-17-2` could both be planned. The
   second note was then skipped as done, or overwritten with `--overwrite`. Names
   are now allocated in two passes: stems you chose on the device are reserved
   first, so a generated suffix can never take one. Three tests pin it, including
   the reachable sorted order.
2. **A rerun trusted the `.md` alone.** A note whose `.pdf` was lost stayed skipped
   forever behind a broken embed. `run` now needs both files before it skips, and
   `write_note_outputs` stages both files and renames them into place, so a file
   that exists is one that was written in full.

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

### PR #5 — page markers, progress, max_pixels investigation

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

### PR #7 — standard HF cache location

- **`_default_hf_home()` / `Path.home()` failure mode: gone.** The `RuntimeError` risk
  on an unresolvable home directory disappeared with the function — nothing in the
  package resolves a home path any more.
- **`requirements-dev.txt` was unusable with uv.** The quoted `-e ".[dev,transcribe]"`
  parses under pip but not uv (`Expected package name starting with an alphanumeric
  character, found '"'`). Unquoted; works under both.
- **Homebrew `python@3.13` can vanish** (only `python@3.14` remains), which kills the
  venv since its interpreter is gone. `uv venv --python 3.13` rebuilds it without
  adding a second CPython to the Homebrew tree; both routes are documented.

### PR #9 — repo review (2026-08-10, no in-flight branch)

Full-repo health check: internal `/code-review high` over `src/` + `tests/`, plus
external Codex (agentic, read-only) and Gemini (inlined source) reviews. 40/40
tests green, ruff clean going in. Two doc-drift items were fixed in the pass
itself; every code finding was triaged into Known Issues / Enhancements above
(none observed in real runs, so nothing was hot-fixed):

1. **Stale `test_vlm_eval.py` docstring** *(internal + Codex)* — claimed `HF_HOME`
   is "set on import of `transcribe`", the exact behavior PR #7 removed and the
   CLAUDE.md never-set-`HF_HOME` invariant forbids. Rewritten to describe the
   standard-cache behavior.
2. **ARCHITECTURE "no network call at conversion time"** *(Codex)* — contradicted
   the documented first-run weight download; now qualified (offline once weights
   are cached).

Rejected reviewer findings (verified against the code before dismissal): the
`max(1, …)` downscale-cap escape (unreachable for Supernote's fixed 1920×2560
pages), argparse prefix-matching on `--page-separators` (no longer a prefix of any
flag), `Image.LANCZOS` deprecation (still a valid alias in current Pillow), and
"`note_to_pdf` has no tests" (raster mode is exercised by the pipeline integration
test's `%PDF-` assertion; only vector mode is uncovered — tracked under
Enhancements).

### Runtime validation (2026-07-17)

- **Transcription accuracy on real handwriting.** The first real-folder conversion
  ran clean — the default Qwen3-VL-30B handled the actual notes well, no issues.
  Retires the core "does the default model work on real handwriting" risk (it was the
  main open question). Fallbacks stay documented (`olmOCR-7B`, `Qwen2.5-VL-7B`); wider
  corpus coverage accrues with continued use.

## Unknowns

Least-confident areas and open risks.

- **mlx-vlm API stability.** `generate`/`apply_chat_template` signatures were pinned
  against 0.6.5; 0.6.10 is installed today and the suite is green. A future upgrade
  could shift them; the transcriber is small
  and isolated, so a break is contained to `transcribe.py`. (We do **not** rely on
  `load(**kwargs)` forwarding processor args — PR #5 found that path silently discards
  `max_pixels`, which is why the pixel cap is a pre-render downscale in `convert.py`.)
- **The 1.5M pixel cap is empirical and default-model-specific.** It guards the
  Qwen3-VL empty-generation cliff and can't be derived from model metadata (PR #5).
  A different `--model` may have a different safe ceiling; there's no runtime check
  that the chosen cap is safe for the chosen model — the `vlm` eval covers only the
  default model, and only when cached. Silent empty output on an untested model+cap
  combination remains possible; `--max-pixels` is the manual lever.
- **Nothing verifies where weights actually landed.** With `HF_HOME` no longer set by
  the tool, a user who expected `~/Local-Models` but never exported `HF_HOME` silently
  gets a second copy in `~/.cache/huggingface`. The failure mode is disk use and a
  re-download, not wrong output, so there's no runtime check — `hf cache scan` is the
  manual lever.

- **How name comparison lines up with filesystem rules.** Planned names are compared
  as raw Python strings, while macOS ignores case and Unicode normalization
  differences. Two names we treat as separate could point at one file. On this Mac's
  APFS volume the two source files cannot sit in one folder anyway, so this matters
  mainly on case-sensitive volumes.

## Notes

- The PDF and the Markdown are written as two steps, not one. Each file lands
  atomically, but an interrupted `--overwrite` can leave a new PDF beside the old
  Markdown. Both files exist, so the next run skips the note. Closing this needs a
  marker written after both land, which is a lot of machinery for a gap of two
  operations.
- Reading `.note` files from a cloud-synced folder (Google Drive File Stream,
  iCloud, Dropbox) is slow, since files download on demand. A slow folder run is
  input I/O, not a conversion bug — conversion itself is ~1 s/note.
- Python 3.14 is unsupported (dependency wheels); supported range is 3.10–3.13. If
  Homebrew's `python@3.13` is gone (only 3.14 remains), `uv venv --python 3.13` builds
  the venv without adding a second CPython to the Homebrew tree.
- **Keeping weights outside `~/.cache/huggingface` is a shell-profile decision, not a
  tool setting.** Hugging Face resolves its cache from `HF_HOME` (or the narrower
  `HF_HUB_CACHE`) and never searches for an existing tree, so `export
  HF_HOME=~/Local-Models` in `~/.zshrc` is what points every HF tool — this one
  included — at a shared location. Weights under a cache the env vars don't name are
  simply invisible; `hf cache scan` lists what's where, `hf cache delete` reclaims
  duplicates.
- PySN was considered and not adopted; `supernotelib` covers all conversion needs.
