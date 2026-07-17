# ROADMAP — SupernoteExport

## Status

**Phase 1 — Ad-hoc conversion pipeline: implemented.**
`.note` → PDF + transcribed Markdown, one pair per note, local MLX-VLM transcription,
mirrored subfolder output. Suite green: deterministic layers unit-tested, plus a
real-`.note` integration test. (No test count here on purpose — nothing verifies it, and
a hand-maintained number goes stale silently.)

**Phase 2 — Post-rename cleanup: done** (merged, PR #1).
Repo renamed `SupernoteSync` → `SupernoteExport`; package renamed to match
(`supernote_export`, CLI `python -m supernote_export`); machine-specific hardcoding
removed (`HF_HOME` default via `Path.home()`, test path via `SUPERNOTE_TEST_NOTE`);
`ARCHITECTURE.md` added with a generated diagram.

**Phase 3 — Committed test fixture + VLM eval: in progress** (`feature/fixture-note`).
A disposable sample note (`tests/fixtures/20260717_012708.note`) is committed and the
integration tests point at it directly. `SUPERNOTE_TEST_NOTE` is **removed**: with a
real note in the repo, an env var whose only accepted value must match the fixture's
asserted stem and page count was a trap, not a knob. The default suite now runs with no
setup. The fixture also enables an **opt-in VLM eval** (`pytest -m vlm`, deselected by
default) that runs the real model end-to-end and asserts tolerant properties — its job
is to catch the empty-output resolution cliff, the one silent failure this project has
actually hit. First eval run on the fixture: near-perfect transcription, including the
deliberately-sloppy block; only layout/spatial fidelity (columns, an annotation arrow)
is lost, which is expected for linear Markdown.

## Confidence check (least-confident areas)

1. **Transcription accuracy on the user's handwriting** — the default Qwen3-VL-30B has
   not yet been judged against real pages for fidelity. This is the main open question;
   validated during the first real run and by spot-checking output. Fallbacks documented
   (`olmOCR-7B`, `Qwen2.5-VL-7B`).
2. **mlx-vlm API stability** — `generate`/`apply_chat_template` signatures were pinned
   against installed 0.6.5. A future upgrade could shift them; the transcriber is small
   and isolated, so a break is contained to `transcribe.py`.
3. **Resolved — VLM image-size cliff.** First real batch produced empty transcriptions
   for 5/7 notes. Root-caused to image resolution: a measured scale sweep on a failing
   page showed reliable, *deterministic* output at ≤1.77M px and consistent **empty**
   output at ≥2.76M px (native ~4.9M). `note_to_page_images` now caps at `--max-pixels`
   (default 1.5M). Replaced the old `--image-scale` multiplier, which was the wrong lever.

## Planned / unscheduled enhancements

- **Packaging for install-from-GitHub** — `pyproject.toml` currently declares
  `[project]` metadata but **no `[build-system]`**, so nothing builds or installs; the
  package imports only via pytest's rootdir `sys.path` insertion. To make
  `pip install git+ssh://…` work: add a `[build-system]` table, declare runtime
  dependencies in `[project.dependencies]` (single-sourced, with `requirements.txt`
  reduced to `-e .`), add a `[project.scripts]` console entry point, and add a LICENSE
  (there is none — without one the repo is "all rights reserved" and legally
  un-installable by others even if public).
- **Per-page structure in the `.md`** — optional page headers/markers instead of a bare
  `---` separator, if the user wants page-addressable notes.
- **`max_pixels` control** — expose the VLM processor's pixel cap for small-text pages,
  a more effective knob than post-render upscaling.
- **Front-matter** — optional YAML (source path, capture date, page count, model used)
  for Obsidian Dataview.
- **Progress output** — per-note progress line during long batches (currently only a
  final summary).
- **Watch/auto-sync mode** — deferred by design; invocation stays ad-hoc.
- **Model comparison harness** — quick side-by-side of the three shortlisted models on a
  handful of real pages, to pick empirically if the default disappoints.

## Known issues / notes

- Reading `.note` files from a cloud-synced folder (Google Drive File Stream, iCloud,
  Dropbox) is slow, since files download on demand. A slow folder run is input I/O, not a
  conversion bug — conversion itself is ~1 s/note.
- Python 3.14 unsupported (dependency wheels); pinned to 3.13.
- PySN intentionally not used; supernotelib covers all conversion needs.

## Review findings (end-of-phase)

### Phase 1

To be completed after the first real transcription run and a `/code-review` + `/simplify`
pass. Trivial/safe fixes applied in-phase; anything larger recorded here.

### Phase 2 — post-rename cleanup (2026-07-17)

`/code-review high` over the branch. Every finding was **documentation drift introduced by
the phase itself**, not a logic defect — the code changes were a rename, a
`Path.home()`-based default, and a test fixture. All four were fixed in-branch:

1. **`CLAUDE.md` claimed the integration test "skips if absent"** — it now fails loudly
   instead. Directly contradicted the code and would have misled the next session.
2. **`ROADMAP.md` claimed 26 tests** after the new `_default_hf_home` test made it 27.
   (This is the second time the hardcoded count went stale in one session — see the
   confidence note below.)
3. **`build_architecture.py` re-found its own `<diagram>` element** via
   `mxfile.find("diagram")` instead of using the variable assigned two lines above.
   Refactored; verified the generated `.drawio` is byte-identical afterwards.
4. **`CLAUDE.md` didn't mention `ARCHITECTURE.md`** or that the diagram is generated —
   a future session would likely have hand-edited the `.drawio` XML or the PNG.

**Deliberately not fixed** (tracked above under planned enhancements): the integration
test's note-specific assertions, and the absent packaging config. Neither is a regression.

### Confidence check — least confident areas

1. **~~The `SUPERNOTE_TEST_NOTE` contract is weaker than it looks.~~** *Resolved in
   Phase 3:* the env var was removed in favour of a committed fixture the tests point at
   directly. The stem/page-count assertions are now honest — they describe a file the
   repo owns, not a hidden constraint on an env var's value.
2. **~~Hardcoded counts in prose go stale silently.~~** *Resolved in-phase:* the ROADMAP
   test-count claim drifted twice in one session, so the number was removed rather than
   reset. Watch for the same pattern in other hand-maintained figures.
3. **`_default_hf_home()` assumes `Path.home()` resolves.** It raises `RuntimeError` if the
   home directory can't be determined (no `HOME`, some CI sandboxes). Acceptable for a
   local CLI on macOS; would need a guard if this ever ran in a container.
