# Enhancements

Candidate work, highest priority first. [ROADMAP.md](ROADMAP.md) carries the one-line index;
this file carries enough detail to pick an item up without digging.

Each entry has a stable ID — use it in branch names (`feature/enh-01-<slug>`) and in the
CHANGELOG entry that closes it. When an item ships, delete it from here and from the ROADMAP
index; the record lives in [CHANGELOG.md](../CHANGELOG.md). An item dropped rather than built
moves to "Decisions taken and not taken" in [CLAUDE.md](../CLAUDE.md).

**IDs are assigned in ascending order and never reused**, including after an entry is
deleted. The next free ID is **ENH-11**.

Entries are ordered by priority, then by ascending ID. Nothing here is scheduled.

## Priority

Priority is about value, not urgency. Effort is a rough estimate — a session, or days.

| Level | Means |
|-------|-------|
| **High** | Closes a gap hit during real use. |
| **Medium** | Worth doing when the area is already open. Removes a sharp edge or a duplication. |
| **Low** | Tidying. Do it while passing through. |

---

<a id="enh-01"></a>
## ENH-01 — Load each notebook once instead of twice per note

**Priority:** Medium · **Effort:** ~2 hours
**Where:** [convert.py:34-70](../src/supernote_export/convert.py#L34-L70), [pipeline.py:72-77](../src/supernote_export/pipeline.py#L72-L77) · **Regression net:** `tests/test_convert.py`, `tests/test_pipeline.py`
**Source:** gpt-5.6-sol — full-codebase review
**Reconfirmed:** gpt-5.6-sol — repo review, 2026-09-01

### What it is

`note_to_pdf` and `note_to_page_images` each call `_load` on the same file:

```python
def _load(note_path: Path | str) -> sn.Notebook:
    return sn.load_notebook(str(note_path))
```

So a note that gets both a PDF and a transcription is read from disk and parsed twice.

Load it once in `pipeline.run` and pass the `Notebook` to both, or add one `convert` helper
that returns the PDF bytes and the page images together.

### Why it matters

Every note is read and parsed twice for no reason. That is a plain duplication in the hot path
of the batch.

Be careful with the size of the claim: the first read is what pulls a cloud-synced file down,
and the second reads the local copy, so this does **not** double the download. It doubles the
parse and the second disk read. Nobody has reported a run being slow because of it, which is
why this is Medium and not High — it removes a duplication rather than closing a gap hit in
real use. Measure before assuming the saving is large.

There is a second, better reason than speed. The two loads are separate reads of a file that a
sync client may be rewriting, so the archival PDF can come from one revision of the note and
the transcription from another, with nothing to show it happened. The window is about a second
and needs a sync landing inside it, so this is a sharp edge rather than an observed failure —
but loading once closes it, which speed alone does not justify. Related:
[KI-15](KNOWN_ISSUES.md#ki-15) is the same class of staleness at a coarser grain.

### Notes for the work

Changing `note_to_pdf` and `note_to_page_images` to accept a `Notebook` instead of a path
moves the loading decision to the caller, which is where the batching context lives. Keep
path-accepting wrappers if the current signatures are worth preserving for library callers.

A combined helper pairs naturally with [ENH-06](#enh-06): if the page images become an
iterator, the helper returns the PDF bytes plus that iterator from a single load.

Constraint: `tests/test_convert.py` calls both functions with a path against the committed
fixture, and `tests/test_pipeline.py` asserts the transcriber sees the fixture's three pages.

---

<a id="enh-02"></a>
## ENH-02 — Validate options at the library seam, not just in argparse

**Priority:** Medium · **Effort:** ~3 hours
**Where:** [pipeline.py:30-50](../src/supernote_export/pipeline.py#L30-L50), [convert.py:38-46](../src/supernote_export/convert.py#L38-L46), [transcribe.py:85-93](../src/supernote_export/transcribe.py#L85-L93) · **Regression net:** `tests/test_pipeline.py`, `tests/test_convert.py`
**Source:** gpt-5.6-sol — full-codebase review
**Reconfirmed:** gpt-5.6-sol — repo review, 2026-09-01

### What it is

`page_markers`, `pdf_mode` and `max_pixels` are checked only by argparse. Call `run()` or
`MlxVlmTranscriber()` directly with a bad value and it silently falls back to a default:

```python
vectorize = pdf_mode == "vector"
```

Anything that is not the string `"vector"` becomes raster. `assemble_transcription` treats any
unrecognized `page_markers` as `"none"`. Neither says a word.

Validate in the functions themselves and raise on an unknown value.

### Why it matters

The package is installable and importable, so `run()` is a public entry point, not just
something the CLI calls. A typo in a caller's `pdf_mode="verctor"` produces raster PDFs that
look plausible and are silently not what was asked for.

### Notes for the work

Decide at the same time what a non-positive `--max-pixels` means. `_downscale_to_max_pixels`
treats any value at or below zero as "no cap":

```python
if max_pixels <= 0 or pixels <= max_pixels:
    return image
```

That is an undocumented way to switch the cap off, and given the resolution cliff
([UNK-02](OPEN_QUESTIONS.md#unk-02)) it is a foot-gun. Either document it as the escape hatch
it is, or restrict it to `0` and reject negatives.

---

<a id="enh-03"></a>
## ENH-03 — Fill the test gaps: failure recovery, CLI exit codes, vector PDF

**Priority:** Medium · **Effort:** ~half a day
**Where:** [pipeline.py:82-84](../src/supernote_export/pipeline.py#L82-L84), [cli.py:80-109](../src/supernote_export/cli.py#L80-L109), [convert.py:49-52](../src/supernote_export/convert.py#L49-L52) · **Regression net:** `tests/test_pipeline.py`, `tests/test_cli.py`, `tests/test_convert.py`
**Source:** internal `/code-review high` — repo review, 2026-08-10
**Reconfirmed:** gemini-3.1-pro-high — repo review, 2026-09-01

### What it is

Three paths have no test:

- **Per-note failure recovery.** `pipeline.run` catches per note and appends to
  `Summary.failed`, which is a named invariant, and nothing exercises it.
- **`cli.main`'s exit code and summary output.** `_print_summary` and the
  `return 1 if summary.failed else 0` line are uncovered.
- **Vector `--pdf-mode`.** Raster is covered by the pipeline test's `%PDF-` check; the
  `vectorize=True` branch is not.

### Why it matters

"One bad note must not stop a batch" is the invariant that makes the tool usable over a
folder of real notes, and it is asserted only by reading the code. A refactor that turned the
`except` into a re-raise would pass the whole suite.

### Notes for the work

The failure path is easy to drive with a `Transcriber` that raises: the fake transcriber
pattern is already in `tests/test_pipeline.py`. `cli.main` takes an `argv` list, so it can be
called directly and its return value asserted, with `capsys` for the summary text.

Vector conversion is slower than raster on the fixture but still runs in a test; assert the
`%PDF-` header and that the bytes differ from the raster render.

Related: [KI-10](KNOWN_ISSUES.md#ki-10) adds an exit path that this coverage should include.

---

<a id="enh-04"></a>
## ENH-04 — Make the `vlm` eval's cache check honest

**Priority:** Medium · **Effort:** ~2 hours
**Where:** `tests/test_vlm_eval.py` · **Regression net:** the eval itself, run with `pytest -m vlm`
**Source:** internal `/code-review high` — repo review, 2026-08-10

### What it is

The eval skips itself when the model is not cached, so a checkout without the weights does not
try to download tens of gigabytes. The check looks only for `config.json`, which is the first
file Hugging Face fetches and by far the smallest.

A partly cached model therefore passes the gate, and running `pytest -m vlm` starts a
multi-gigabyte download instead of skipping.

### Why it matters

The skip is the eval's whole safety property. As written it protects the case where nothing
has been fetched, and not the case that actually happens: an interrupted first run.

### Notes for the work

Check for the weight shards, not just the config — the `model*.safetensors` files named in
`model.safetensors.index.json`, verified present in the snapshot directory. `huggingface_hub`
can resolve a cached file without network access, which makes the check cheap and honest.

Constraint: the eval must keep skipping rather than failing when the model is absent. That is
the deliberate opposite of the fixture test, which fails loudly, because the model is huge and
optional while the fixture is cheap and always there.

---

<a id="enh-05"></a>
## ENH-05 — Optional YAML front matter for Dataview

**Priority:** Medium · **Effort:** ~half a day
**Where:** [writer.py:10-20](../src/supernote_export/writer.py#L10-L20), [cli.py:14-70](../src/supernote_export/cli.py#L14-L70) · **Regression net:** `tests/test_writer.py`

### What it is

A flag that puts YAML front matter at the top of each `.md`: source note path, capture date,
page count, and the model that produced the transcription.

### Why it matters

Obsidian's Dataview reads front matter. With it, a vault can list every note captured in a
date range, or every note transcribed by a model you have since replaced — which is the
question you ask when you change `--model` and want to know what to re-run.

The page count is `len(images)`, so that one is in hand at write time. The capture date is
not. `naming.derive_name` returns an output *name*, and for a note renamed on the device it
returns the stem unchanged, with no date in it at all. Decide where the date comes from:
parse the `YYYYMMDD_HHMMSS` filename and omit the field when the stem is not a timestamp, or
read the capture time from the notebook's own metadata through `supernotelib`, which covers
renamed notes too.

### Notes for the work

`build_markdown` is a pure function with unit tests; the front matter belongs there, behind a
parameter, so the tests stay simple. The values have to reach it from `pipeline.run`, which
means widening its signature.

Keep it off by default. A vault that does not use Dataview gains nothing from a header on
every note, and the embed-only `--no-transcribe` output should stay minimal.

---

<a id="enh-06"></a>
## ENH-06 — Stream page images instead of building them all

**Priority:** Medium · **Effort:** ~3 hours
**Where:** [convert.py:55-70](../src/supernote_export/convert.py#L55-L70), [transcribe.py:75-79](../src/supernote_export/transcribe.py#L75-L79) · **Regression net:** `tests/test_convert.py`, `tests/test_pipeline.py`
**Source:** gpt-5.6-sol — full-codebase review
**Reconfirmed:** gemini-3.1-pro-high — repo review, 2026-09-01

### What it is

`note_to_page_images` renders every page before the model sees any of them:

```python
images: list[Image.Image] = []
for page_number in range(notebook.get_total_pages()):
    image = image_converter.convert(page_number)
    images.append(_downscale_to_max_pixels(image, max_pixels))
return images
```

The `Transcriber` protocol takes `list[Image.Image]`, which writes that choice into the
design. An iterator would let each page be rendered, transcribed, and released in turn.

### Why it matters

A long notebook holds every page in memory at once. At the 1.5M-pixel cap that is about 6 MB
per page in RGB, so a 200-page notebook holds well over a gigabyte for no reason — the model
reads one page at a time.

### Notes for the work

Changing the protocol is the real work; `transcribe_pages(images)` is the seam the whole test
strategy rests on. An `Iterable[Image.Image]` still satisfies every current caller and keeps
the fake transcribers in the tests working, but code that calls `len(images)` has to change —
`tests/test_pipeline.py` asserts on exactly that.

Pairs with [ENH-01](#enh-01): one notebook load feeding one lazy page iterator.

---

<a id="enh-07"></a>
## ENH-07 — Skip directories named `*.note` during discovery

**Priority:** Medium · **Effort:** ~1 hour
**Where:** [discover.py:24-26](../src/supernote_export/discover.py#L24-L26) · **Regression net:** `tests/test_discover.py`
**Source:** gpt-5.6-sol — full-codebase review
**Reconfirmed:** gemini-3.1-pro-high — repo review, 2026-09-01

### What it is

`rglob` matches directories as well as files:

```python
notes = sorted(input_path.rglob(f"*{NOTE_SUFFIX}"))
return [(note, note.parent.relative_to(input_path)) for note in notes]
```

A folder called `Archive.note` is returned as a note, and then fails inside `supernotelib`
once per run. Filter on `is_file()`.

### Why it matters

The failure is confusing rather than damaging — the batch continues, and the summary reports a
failure for something that was never a note. But it costs a real conversion slot and an error
line every run until the folder is renamed.

### Notes for the work

Decide at the same time whether `.NOTE` should match. `NOTE_SUFFIX` is compared exactly, both
in the single-file branch and through the `rglob` pattern, so an uppercase extension is
rejected on macOS even though the filesystem is case-insensitive. Matching case-insensitively
is a one-line change; leaving it strict is also defensible, since the device always writes
lowercase.

---

<a id="enh-08"></a>
## ENH-08 — Model comparison harness over real pages

**Priority:** Low · **Effort:** ~1 day
**Where:** `tests/test_vlm_eval.py` is the closest existing machinery

### What it is

A script that runs the shortlisted models over the same few pages and writes their output side
by side, so changing the default is a measurement rather than a guess. The current shortlist is
the default `Qwen3-VL-30B-A3B-Instruct-8bit` plus the two documented alternatives,
`olmOCR-7B-0725-8bit` and `Qwen2.5-VL-7B-Instruct-8bit`.

### Why it matters

The default was chosen by running it and reading the result. That was enough to ship, but it
means there is no record of how the alternatives compare on the handwriting this tool actually
sees — and no way to tell whether a newer model is better without repeating the whole informal
process.

### Notes for the work

This needs real pages, and real pages are personal, so the harness cannot ship with a corpus.
Point it at a local folder the user supplies, and keep the committed fixture as the smoke test.

It also needs each model's safe pixel cap, which cannot be read from metadata — see
[UNK-02](OPEN_QUESTIONS.md#unk-02). A sweep per model is part of the comparison, not a
precondition for it.

---

<a id="enh-09"></a>
## ENH-09 — Drop the `Operating System :: MacOS` classifier

**Priority:** Low · **Effort:** ~15 minutes
**Where:** [pyproject.toml:15-20](../pyproject.toml#L15-L20)
**Source:** gpt-5.6-sol — full-codebase review

### What it is

The package declares itself macOS-only:

```toml
classifiers = [
    "Environment :: Console",
    "Operating System :: MacOS",
    "Programming Language :: Python :: 3",
    "Topic :: Text Processing :: Markup :: Markdown",
]
```

The base install is PDF-only conversion and runs anywhere. Only transcription needs macOS,
and that is already gated behind the `[transcribe]` extra and the lazy MLX import.

### Why it matters

The classifier is what a package index shows and what tooling filters on. It tells a Linux
user the tool will not work for them, which is wrong for everything except the optional extra.

### Notes for the work

Replace it with `"Operating System :: OS Independent"`. The macOS requirement belongs in the
extra's description and in the README's Requirements section, where it already is.

Related: [KI-05](KNOWN_ISSUES.md#ki-05) is the other packaging-metadata item; both are one-line
`pyproject.toml` edits and should ship together.

---

<a id="enh-10"></a>
## ENH-10 — Share the fixture constants through `tests/conftest.py`

**Priority:** Low · **Effort:** ~1 hour
**Where:** `tests/test_pipeline.py`, `tests/test_convert.py`, `tests/test_vlm_eval.py`
**Source:** internal `/code-review high` — repo review, 2026-08-10
**Reconfirmed:** gemini-3.1-pro-high — repo review, 2026-09-01

### What it is

`SAMPLE_NOTE` is defined in three test modules, `SAMPLE_STEM` and `SAMPLE_PAGES` in two each.
A `tests/conftest.py` would hold one copy.

### Why it matters

The project CLAUDE.md tells anyone swapping the fixture to update `SAMPLE_STEM` and
`SAMPLE_PAGES` in `test_pipeline.py`. That instruction is already incomplete — the same
constants live in two other files — so following it leaves the suite broken in a way the
instruction says it should not be.

### Notes for the work

Move all three to `tests/conftest.py`, as module constants or fixtures, and update the project
CLAUDE.md's testing section to name the one place. Keep the values themselves unchanged so the
assertions stay pinned to the committed fixture's real properties.
