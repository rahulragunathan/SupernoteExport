# ROADMAP — SupernoteExport

Fixed sections, kept up to date: **Status**, **Known Issues**, **Enhancements**,
**Resolved**, **Unknowns**, **Notes**.

## Status

Milestones and how far each one got. Anything Done names the PR that closed it.

- **Phase 1 — Conversion pipeline: Done** (baseline, `75e455e`).
  Turns a `.note` into a PDF and a transcribed Markdown file, one pair per note.
  Transcription runs on a local MLX-VLM model. The output folder mirrors the input
  tree.
- **Phase 2 — Post-rename cleanup: Done** (PR #1).
  Renamed the repo to SupernoteExport and the package to `supernote_export`.
  Removed machine-specific paths. Added ARCHITECTURE.md and its generated diagram.
- **Phase 3 — Test fixture and VLM eval: Done** (PR #2).
  Added a sample `.note` to the repo, so the integration tests run anywhere with no
  setup. Dropped the `SUPERNOTE_TEST_NOTE` variable. Added an opt-in eval
  (`pytest -m vlm`) that runs the real model.
- **Phase 4 — Packaging and MIT license: Done** (PR #3).
  Moved to a `src/` layout built by hatchling. Dependencies now live only in
  `pyproject.toml`. Made `mlx-vlm` the optional `[transcribe]` extra, so the base
  install works on any platform. Added the `supernote-export` command and an MIT
  license.
- **Phase 5 — Output and progress controls: Done** (PR #5).
  Added `--page-markers {none,line-break,page-numbers}` in place of
  `--page-separators`. Page numbers follow the real source page, so a blank page
  leaves a gap instead of renumbering the rest. The CLI now prints one line per
  note. Also investigated `max_pixels` and closed it — see Resolved.
- **Phase 6 — Standard Hugging Face cache: Done** (PR #7).
  The tool no longer sets `HF_HOME`. Weights go to `~/.cache/huggingface` unless you
  set `HF_HOME` yourself. A test starts a fresh interpreter to prove the import
  leaves the variable alone.
- **Phase 7 — Output naming and skip integrity: Done** (PR #10).
  Names are allocated in two passes, so a name you chose on the device is never
  taken by a generated suffix. A note is skipped only when both its outputs exist.
  Both files are staged and renamed into place.

## Known Issues

Bugs we can reproduce. Non-bug caveats go under Notes. Open risks go under
Unknowns.

Two reviews found these: the PR #9 repo review (internal `/code-review high`,
Codex, and Gemini) and a later full-codebase review by GPT-5.6-Sol. Each one was
checked against the code. None has shown up in a real run yet.

### The tool can lose a note

- **Names shift between runs.** Each run works out names from the notes it can see,
  so two runs that see different notes hand out different names. Convert one note
  from 17 August today and a second one tomorrow: both are named `2025-08-17`, and
  the tool skips the second without a word. A note that syncs down late shifts every
  suffix in that folder, so older notes get skipped and one note is written twice.
  Reserving names inside a run does not help — PR #10 does exactly that and this
  still stands. The tool has to remember which note produced which file, which needs
  its own phase.
- **A stray PDF gets overwritten.** If `<name>.pdf` exists in the output folder but
  `<name>.md` does not, the run converts the note and replaces that PDF, even
  without `--overwrite`. A PDF that came from somewhere else is gone.

### Transcription can fail and still look successful

- **A dropped page looks like a blank page.** The model sometimes returns nothing
  for a page. `assemble_transcription` drops empty pages, so that page vanishes from
  the Markdown. With `--page-markers page-numbers` the gap looks exactly like a page
  that was blank on purpose. When every page comes back empty, the result is an
  embed-only `.md` that still reports success — the signature of the resolution
  cliff in Resolved. A fix has to tell a blank page from a failed one without
  trusting the model's own output.
- **A long page is cut off in silence.** `_transcribe_one` stops at 4,096 tokens and
  keeps only the text. `mlx-vlm` reports `finish_reason == "length"` when it hits
  that cap, and we ignore it. A dense page is written out as a finished note.
- **Indentation on a page's first line is stripped.** `assemble_transcription` and
  `_strip_code_fence` both call `strip()`. If a page starts with an indented list or
  block, that indent is lost — the opposite of what the prompt asks the model to
  preserve.

### Bad input or a partial install fails badly

- **A wrong `--input` prints a traceback.** `discover_notes` raises before the
  per-note error handling, and `cli.main` does not catch it. A typo gives you a
  stack trace instead of one clear line.
- **A missing `[transcribe]` extra fails once per note.** Install the base package,
  forget `--no-transcribe`, and the tool renders every PDF and then fails each note
  with `ModuleNotFoundError: mlx_vlm`. It should check once, up front, and say what
  to install.
- **A half-loaded model breaks the rest of the batch.** `_ensure_loaded` sets
  `self._model` before it loads the config. If the config load fails, the per-note
  handler swallows the error, and every later note skips loading and fails with an
  unrelated one. Set all three attributes only after every load succeeds.

### Markdown output can break in Obsidian

- **Some filenames break the embed.** `build_markdown` drops the filename straight
  into `![[...]]`. Obsidian reads `[` and `]` as link syntax, `|` as an alias, and
  `#` as a heading link, so a note called `Status #2` or `A|B` points at the wrong
  file or fails to embed.
- **A page that starts with a code fence gets mangled.** `_strip_code_fence` assumes
  an opening fence came from the model, not from your notes. When the page really
  does start with a fenced snippet, it deletes the opening fence and leaves the
  closing one, so the rest of the page renders as code.

## Enhancements

Not scheduled unless the item says so.

- **Front matter** — optional YAML (source path, capture date, page count, model)
  for Obsidian Dataview.
- **Watch mode** — deferred on purpose. You run the tool when you want it.
- **Model comparison harness** — run the shortlisted models over a few real pages
  side by side, so swapping the default is a measurement rather than a guess.
- **Load each notebook once** — `note_to_pdf` and `note_to_page_images` each call
  `load_notebook` on the same file, so every note is read and parsed twice. On a
  cloud-synced folder that doubles the slowest part of a run.
- **Stream pages instead of holding them all** — `note_to_page_images` builds every
  page image before the model sees any of them, and the `list[Image]` protocol
  writes that into the design. An iterator would cut memory on long notebooks and
  pairs well with loading each notebook once.
- **Check options at the library seam** — `page_markers`, `pdf_mode`, and
  `max_pixels` are checked only by argparse. Call `run()` or `MlxVlmTranscriber()`
  directly with a bad value and it quietly falls back to the default. Decide as well
  whether `--max-pixels 0` should stay an undocumented way to switch the cap off.
- **Make discovery stricter** — skip directories named `*.note`, which `rglob`
  returns and which then fail per note. Decide whether `.NOTE` should match.
- **Fill the test gaps** — per-note failure recovery, `cli.main` exit codes and
  summary output, and vector `--pdf-mode`. Raster is already covered by the pipeline
  test's `%PDF-` check.
- **Share the fixture constants** — `SAMPLE_NOTE`, `SAMPLE_STEM`, and `SAMPLE_PAGES`
  are copied into three test modules. A `tests/conftest.py` would hold one copy.
- **Fix the packaging metadata** — `requires-python` has no `<3.14` bound, though
  every doc says 3.14 does not work, so pip will start an install that cannot find
  wheels. The `Operating System :: MacOS` classifier is also wrong for the PDF-only
  install.
- **Make the eval's cache check honest** — `_require_cached_model` looks only for
  `config.json`, so a partly cached model can still download gigabytes when you run
  `pytest -m vlm`.

## Resolved

Closed issues and end-of-phase findings, grouped by PR.

### PR #10 — output naming and skip integrity

Two of the seven bugs from the PR #9 review. Both came from the pipeline trusting a
signal that did not mean what it assumed.

1. **One run could plan the same name twice.** `plan_output_names` counted base
   names and never reserved the finished ones, so a note renamed on the device to
   `2025-08-17-2` and a date-derived `2025-08-17-2` could both be planned. The second
   note was then skipped as done, or overwritten with `--overwrite`. Names now come
   from two passes: stems you chose on the device are reserved first, so a generated
   suffix can never take one. Three tests pin it, including the sorted order that
   discovery really produces.
2. **A rerun trusted the `.md` alone.** A note whose `.pdf` was lost stayed skipped
   forever behind a broken embed. `run` now needs both files before it skips, and
   `write_note_outputs` stages both files and renames them into place, so a file
   that exists is one that was written in full.

GPT-5.6-Sol reviewed the plan and returned ten findings. Nine were taken, including
two passes instead of one, unique temp filenames, staging both files before
publishing either, and three writer tests that actually exercise the atomic path.
The tenth asked for a manifest so both files land as one transaction; that is
recorded under Notes instead.

### Phase 1 (baseline)

- **The VLM has a resolution cliff.** The first real batch produced empty
  transcriptions for five notes out of seven. Image size was the cause. A measured
  sweep on a failing page gave reliable output at or below 1.77M pixels and empty
  output at or above 2.76M; a full page is about 4.9M. `note_to_page_images` now
  caps pages at `--max-pixels`, default 1.5M. This replaced `--image-scale`, which
  was the wrong control.

### PR #1 — post-rename cleanup

A `/code-review high` over the branch. Every finding was documentation the phase
itself had made stale, not a logic bug. All fixed in the branch:

1. CLAUDE.md said the integration test "skips if absent". It fails loudly.
2. ROADMAP carried a hand-counted number of tests. It had drifted twice, so we
   removed the number rather than update it. Watch for the same habit in other
   hand-kept figures.
3. `build_architecture.py` looked up its own `<diagram>` element instead of using
   the variable two lines above. Refactored; the generated file stayed identical.
4. CLAUDE.md did not mention ARCHITECTURE.md or that the diagram is generated.

### PR #2 — committed fixture

- **`SUPERNOTE_TEST_NOTE` promised more than it delivered.** It read like "point
  this at any note", but the tests assert one sample's name and page count, so any
  other note failed with a confusing error. A committed fixture replaced it. The
  assertions now describe a file the repo owns, and nobody has to set anything up.

### PR #5 — page markers, progress, and the max_pixels investigation

1. **Per-page structure.** `--page-separators` became
   `--page-markers {none,line-break,page-numbers}`. The joining logic moved into
   `assemble_transcription`, a pure function with unit tests. Page numbers use the
   real source page, so a blank page leaves a gap and the headers still line up with
   the PDF.
2. **`max_pixels` — tried, reverted, closed.** We first swapped the pre-render
   downscale for the model processor's own `max_pixels`. The eval passed, but that
   was false confidence: mlx-vlm rebuilds the image processor from
   `preprocessor_config.json` and throws the argument away, so the real cap stayed at
   the model default of 16.7M. A real note then produced an embed-only `.md`. We
   instrumented the boundary to prove it. We also checked whether the safe cap can be
   read from model metadata. It cannot — the safe point sits below everything the
   model advertises: 1.5M works, while 2.0M, 2.36M
   (`num_position_embeddings × (patch·merge)²`), and 16.7M (`size.longest_edge`) all
   return empty. So 1.5M stays a hard-coded conservative number, with `--max-pixels`
   as the control for other models. A deterministic cap test in `note_to_page_images`
   is now the main guard, because the eval can pass by luck. The eval's anchor match
   also became case-insensitive.
3. **Progress output.** `pipeline.run` gained an
   `on_progress(index, total, path, status)` callback, and the CLI prints one line
   per note to stderr. The library still prints nothing.

### PR #7 — standard Hugging Face cache

- **`_default_hf_home()` is gone**, and with it the `RuntimeError` risk when the home
  directory could not be resolved. Nothing in the package looks up a home path now.
- **`requirements-dev.txt` did not work with uv.** The quoted `-e ".[dev,transcribe]"`
  parses under pip but not under uv. Unquoted, both accept it.
- **Homebrew's `python@3.13` can disappear**, which breaks the venv because its
  interpreter is gone. `uv venv --python 3.13` rebuilds it without adding a second
  CPython to the Homebrew tree. Both routes are documented.

### PR #9 — repo review (2026-08-10, no branch in flight)

A full health check: internal `/code-review high` over `src/` and `tests/`, plus
Codex and Gemini. 40 tests green and ruff clean going in. Two stale docs were fixed
in the pass:

1. `test_vlm_eval.py` still said `HF_HOME` is "set on import of `transcribe`" — the
   behavior PR #7 removed.
2. ARCHITECTURE said there is "no network call at conversion time", which ignored the
   first-run weight download. Now qualified.

Every code finding went to Known Issues or Enhancements instead of a hot fix,
because none had appeared in a real run. Four reviewer findings were checked and
rejected: the `max(1, …)` downscale escape (unreachable at Supernote's fixed
1920×2560 page size), argparse prefix matching on `--page-separators` (no longer a
prefix of any flag), `Image.LANCZOS` deprecation (still valid in current Pillow),
and "`note_to_pdf` has no tests" (raster is covered by the pipeline test's `%PDF-`
check; only vector is uncovered).

### Runtime validation (2026-07-17)

- **The default model handles real handwriting.** The first conversion of a real
  folder ran clean, which closed the main open question at the time. The fallback
  models stay documented (`olmOCR-7B`, `Qwen2.5-VL-7B`), and wider coverage builds up
  as the tool gets used.

## Unknowns

Where our confidence is lowest.

- **How stable the mlx-vlm API is.** `generate` and `apply_chat_template` were pinned
  against 0.6.5. 0.6.10 is installed today and the suite is green. A future release
  could move them again. The transcriber is small and isolated, so a break stays
  inside `transcribe.py`. We do not rely on `load(**kwargs)` passing processor
  arguments through — PR #5 proved it drops them.
- **Whether 1.5M pixels is safe for other models.** The cap was measured against
  Qwen3-VL and cannot be read from model metadata. Another `--model` may have a
  different limit, and nothing checks at runtime. The eval covers only the default
  model, and only when it is cached. Silent empty output on an untested model and cap
  is still possible; `--max-pixels` is the manual control.
- **Where the weights actually landed.** The tool no longer sets `HF_HOME`, so
  someone who expected `~/Local-Models` but never exported the variable quietly gets
  a second copy under `~/.cache/huggingface`. That costs disk space and a
  re-download, not correctness, so there is no runtime check. `hf cache scan` shows
  what is where.
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
- Reading `.note` files from a cloud-synced folder (Google Drive, iCloud, Dropbox) is
  slow, because the files download on demand. Conversion itself takes about a second
  per note, so a slow run is input I/O, not a conversion bug.
- Python 3.14 does not work, because the dependencies have no wheels for it. The
  supported range is 3.10 to 3.13. If Homebrew has dropped `python@3.13` and left
  only 3.14, `uv venv --python 3.13` builds the venv without adding a second CPython
  to the Homebrew tree.
- **Keeping weights outside `~/.cache/huggingface` is a shell setting, not a tool
  setting.** Hugging Face reads `HF_HOME` (or the narrower `HF_HUB_CACHE`) and never
  searches for an existing tree. So `export HF_HOME=~/Local-Models` in `~/.zshrc` is
  what points every Hugging Face tool, this one included, at a shared location.
  Weights under a cache the variables do not name are invisible. `hf cache scan`
  lists what is where, and `hf cache delete` reclaims duplicates.
- PySN was considered and not adopted. `supernotelib` covers everything the
  conversion needs.
