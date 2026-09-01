# Known Issues

Open defects, most severe first. [ROADMAP.md](ROADMAP.md) carries the one-line index; this
file carries enough detail to pick an item up without digging.

Each entry has a stable ID — use it in branch names (`bugfix/ki-02-<slug>`) and in the
CHANGELOG entry that closes it. When fixed, delete it from here and from the ROADMAP index;
the record lives in [CHANGELOG.md](../CHANGELOG.md).

**IDs are assigned in ascending order and never reused**, including after an entry is
deleted. The next free ID is **KI-12**.

Entries are ordered by severity, then by ascending ID.

None of these has been seen in a real run. They came out of code review, and each one has
been re-checked against the code as it stands today.

## Severity

| Level | Means |
|-------|-------|
| **Critical** | Loses or corrupts data, or sends wrong information to real recipients. |
| **High** | Silently produces a wrong result, or reports success without doing the work. |
| **Medium** | Wrong under conditions the operator can notice or work around. |
| **Low** | Cosmetic, or wrong in a field nothing consumes. |

---

<a id="ki-01"></a>
## KI-01 — Output names shift between runs, so a note is skipped or written twice

**Severity:** Critical
**Where:** [pipeline.py:52-59](../src/supernote_export/pipeline.py#L52-L59), [naming.py:29-63](../src/supernote_export/naming.py#L29-L63)
**Source:** internal `/code-review high`, gpt-5.6-sol, gemini-3.1-pro-high — repo review, 2026-08-10

### What happens

`plan_output_names` works out names from the notes in **one batch**. It never reads the
output folder, so a second run over a different set of notes hands out different names for
the same files.

```python
notes = discover_notes(input_path)
planned = plan_output_names([(note, output_root / subdir) for note, subdir in notes])
total = len(planned)

summary = Summary()
for index, (note_path, out_dir, name) in enumerate(planned, start=1):
    md_path = out_dir / f"{name}.md"
    pdf_path = out_dir / f"{name}.pdf"
```

`pipeline.run` then treats the planned name as a stable identity — it decides whether a note
was already converted by asking whether `<name>.md` and `<name>.pdf` exist. The name is
per-run; the skip check assumes it is per-note.

The two-pass reservation added in 0.7.0 does not help. It makes names stable *within* a run,
which is a different property.

### Example scenario

You write two notes on 17 August. Today only the first has synced down, so it converts to
`2025-08-17.md`. Tomorrow the second syncs and you run the tool again over the same folder.
Now `plan_output_names` sees both notes: the first still takes `2025-08-17`, the second takes
`2025-08-17-2`. That is correct.

Now reverse the sync order. The note that arrives late sorts *first* in
`discover_notes`, so it claims `2025-08-17` — the name the other note already owns on disk.
The tool sees both outputs present, reports the note as skipped, and never converts it. The
note that did convert yesterday is now filed under a name that belongs to a different note.

Any late arrival in a folder shifts every suffix after it. Notes already written are skipped
under the wrong identity, and one note is written twice.

### Notes for a fix

Two directions, and they are not equivalent:

- **Keep a mapping in the output folder** — source note to output name — and consult it
  before allocating. Names stay human-readable and existing output keeps working, but the
  tool gains a state file it has to keep honest.
- **Derive the name from something inside the note that never changes.** A note then always
  lands on the same name whatever else is in the batch. This makes the name a function of the
  note alone, which is the property the skip check already assumes, but it changes what an
  output file is called.

Both change the meaning of an output name and both need a decision about migrating output
already on disk, so this needs its own phase.

Constraints to preserve: naming must stay reproducible without reading the disk for the
*allocation* itself (see the invariant in [CLAUDE.md](../CLAUDE.md)); the two-pass
reservation that keeps device-chosen stems safe must survive; and `tests/test_naming.py`
pins the current allocation order.

Related: [KI-02](#ki-02) is the other half of the skip check trusting a signal that does not
mean what it assumes.

---

<a id="ki-02"></a>
## KI-02 — A stray PDF with no matching `.md` is overwritten without `--overwrite`

**Severity:** Critical
**Where:** [pipeline.py:60-67](../src/supernote_export/pipeline.py#L60-L67)
**Source:** internal `/code-review high`, gpt-5.6-sol, gemini-3.1-pro-high — repo review, 2026-08-10

### What happens

The skip branch asks whether **both** outputs exist. A lone `.pdf` falls through to
`write_note_outputs`, which replaces it.

```python
# Both files must be there. A surviving .md whose .pdf is gone would
# otherwise be skipped forever behind a broken embed.
if not overwrite and md_path.exists() and pdf_path.exists():
    if on_progress is not None:
        on_progress(index, total, note_path, "skip")
    summary.skipped.append(md_path)
    continue
```

Requiring both files is right for the case it was written for: a half-written pair should be
rebuilt. It also means a PDF that came from somewhere else is destroyed, with no
`--overwrite` and no warning.

### Example scenario

Your Obsidian vault already holds `Notes/Meetings/2025-08-17.pdf` — a scan you filed there
by hand months ago. You convert a Supernote note captured on 17 August into the same folder.
There is no `2025-08-17.md`, so the note is not skipped. The run writes a new
`2025-08-17.pdf` over your scan. The tool reports one note converted and exits zero.

### Notes for a fix

Decide what a lone PDF means. Two defensible answers:

- **Treat it as a half-written output and rebuild it.** That is today's behavior; the fix
  would be to document it in the README rather than change the code.
- **Refuse to touch a PDF that has no matching `.md` unless `--overwrite` is passed**, and
  record the note under `Summary.failed` with a message naming the file.

The second is safer in a shared vault, which is the documented use. It also keeps the
"a file that exists was written in full" invariant intact, because the refusal happens
before any staging.

Related: [KI-01](#ki-01).

---

<a id="ki-03"></a>
## KI-03 — A dropped page is indistinguishable from a blank page

**Severity:** High
**Where:** [transcribe.py:51-59](../src/supernote_export/transcribe.py#L51-L59)
**Source:** internal `/code-review high`, gpt-5.6-sol, gemini-3.1-pro-high — repo review, 2026-08-10

### What happens

The model sometimes returns nothing for a page that has ink on it.
`assemble_transcription` cannot tell that apart from a page that really was blank, so it
drops both.

```python
blocks: list[str] = []
for index, text in enumerate(pages):
    body = text.strip()
    if not body:
        continue  # blank page: dropped, but its number is still used up
    if page_markers == "page-numbers":
        blocks.append(f"## Page {index + 1}\n\n{body}")
    else:
        blocks.append(body)
```

With `--page-markers page-numbers` the gap in the headings looks exactly like a page that was
blank on purpose. With any other marker there is no trace at all.

When *every* page comes back empty the result is a `.md` holding only the embed, and the run
still reports success. That is the signature of the resolution cliff, which is why the
`--max-pixels` cap exists — see [UNK-02](OPEN_QUESTIONS.md#unk-02).

### Example scenario

A twelve-page meeting note transcribes cleanly except for page 7, where the model returns an
empty string. The Markdown runs `## Page 6`, `## Page 8`. Nothing failed, nothing was
logged, and the summary says one note converted. You only find out by reading the embedded
PDF.

### Notes for a fix

The model's own output cannot be trusted to report this — an empty generation is exactly the
failure. The rendered page image is the one place that knows whether a page has ink on it, so
the signal belongs in `convert.note_to_page_images`: return, alongside each image, whether the
page carries handwriting.

The constraint that makes this harder than it sounds: "any pixel differs from the background"
is not the test. A Supernote page can carry a template — ruled lines, a grid, a planner
layout — which renders into the image and is not handwriting. Blank detection has to compare
against the page's own template layer, or ignore it, or accept that it is a heuristic and say
so. `supernotelib` exposes the layers, so the honest version reads the ink layer rather than
the composed image.

`assemble_transcription` can then distinguish the two cases and mark a page that had ink but
produced nothing. Whether that is a warning through `on_progress` or a per-note failure is
the same decision as [KI-04](#ki-04), and the two are worth fixing together.

Constraint: `assemble_transcription` is a pure function with unit tests
(`tests/test_transcribe.py`), and its page-numbering rule — blank pages dropped, their
numbers used up — must survive, because the headings line up with the PDF.

---

<a id="ki-04"></a>
## KI-04 — A page that hits the token cap is written out as finished

**Severity:** High
**Where:** [transcribe.py:106-120](../src/supernote_export/transcribe.py#L106-L120)
**Source:** internal `/code-review high`, gpt-5.6-sol, gemini-3.1-pro-high — repo review, 2026-08-10

### What happens

`_transcribe_one` stops generating at `max_tokens` (4,096 by default) and keeps only the
text. `mlx-vlm` reports `finish_reason == "length"` when it hits that cap, and the value is
discarded with the rest of the result object.

```python
result = generate(
    self._model,
    self._processor,
    formatted,
    image=[image_path],
    max_tokens=self.max_tokens,
    verbose=False,
)
text = getattr(result, "text", result)
return _strip_code_fence(str(text))
```

A dense page is truncated mid-sentence and written into the note as though it were complete.

### Example scenario

A page of small handwriting with a table runs past 4,096 tokens. The transcription stops
halfway through the table. The `.md` shows a partial row, then the next page's heading. The
summary reports the note converted.

### Notes for a fix

The value is already in hand — `getattr(result, "finish_reason", None)`. Two options:

- **Raise**, so `pipeline.run` records the note under `Summary.failed` and the CLI exits
  non-zero. Loud, and it costs the whole note for one page.
- **Keep the partial text and warn** through the `on_progress` callback.

The second fits how the tool treats a lossy transcription generally — the embedded PDF is the
source of truth — but it is not free. `on_progress` today carries two statuses, `"convert"`
and `"skip"`, and is called *before* the slow work; `cli._print_progress` prints anything that
is not `"skip"` as `Converting`. A warning needs a third status, a second call site after the
transcription, and a branch in the printer. Widen the `ProgressCallback` contract and its
comment in `pipeline.py` at the same time.

Whichever is chosen should match [KI-03](#ki-03), so the two silent-failure paths report the
same way.

Constraint: `_transcribe_one` runs once per page inside a loop that holds a
`TemporaryDirectory`; a raise must not leak the scratch files, which the `with` block already
handles.

---

<a id="ki-05"></a>
## KI-05 — Installing on Python 3.14 fails halfway instead of being refused

**Severity:** Medium
**Where:** [pyproject.toml:10](../pyproject.toml#L10)
**Source:** gpt-5.6-sol — full-codebase review

### What happens

The package declares a lower bound and no upper bound:

```toml
requires-python = ">=3.10"
```

So pip and uv treat 3.14 as supported. They accept the interpreter, start resolving, and then
die building a dependency that has no 3.14 wheel. Every doc in the repo says 3.14 does not
work, which makes the metadata the thing that is wrong.

### Example scenario

Homebrew's `python3` is 3.14. Someone follows the README's install line with that
interpreter. Instead of "requires a different Python", they get a compiler error from deep
inside a dependency build, several minutes in, with no indication that the Python version is
the cause.

### Notes for a fix

Change the constraint to `">=3.10,<3.14"`. Installers then refuse the version up front with a
clear message naming the supported range.

Lift the upper bound when the dependencies publish 3.14 wheels. `supernotelib` and `Pillow`
are the base ones; `mlx-vlm` matters only for the `[transcribe]` extra.

Related: [ENH-09](ENHANCEMENTS.md#enh-09) is the other piece of packaging metadata that does
not match reality.

---

<a id="ki-06"></a>
## KI-06 — A half-loaded model poisons every later note in the batch

**Severity:** Medium
**Where:** [transcribe.py:98-104](../src/supernote_export/transcribe.py#L98-L104)
**Source:** gpt-5.6-sol — full-codebase review

### What happens

`_ensure_loaded` guards on `self._model` but assigns it before the load finishes.

```python
def _ensure_loaded(self) -> None:
    if self._model is None:
        from mlx_vlm import load
        from mlx_vlm.utils import load_config

        self._model, self._processor = load(self.model_name)
        self._config = load_config(self.model_name)
```

If `load_config` raises, `self._model` is already set and `self._config` is still `None`. The
per-note handler in `pipeline.run` swallows the error and carries on. Every later note passes
the `is None` guard, skips loading entirely, and fails inside `apply_chat_template` with an
error that says nothing about the real cause.

### Example scenario

The model weights download but `config.json` is truncated by an interrupted transfer. Note 1
fails with the truncation error. Notes 2 through 40 each fail with a `NoneType` error from
`apply_chat_template`. The summary lists forty failures, thirty-nine of which name the wrong
problem.

### Notes for a fix

Load into locals and assign all three attributes only after every step succeeds:

```python
model, processor = load(self.model_name)
config = load_config(self.model_name)
self._model, self._processor, self._config = model, processor, config
```

That restores the guard's meaning — `self._model is not None` means "fully loaded" — and lets
the next note retry the load instead of failing on stale state.

Constraint: the MLX imports must stay inside the method. That is a named invariant in
[CLAUDE.md](../CLAUDE.md), guarded by a subprocess test, and it is what keeps
`--no-transcribe` and the default suite model-free.

---

<a id="ki-07"></a>
## KI-07 — `[`, `]`, `|` and `#` in a name break the Obsidian embed

**Severity:** Medium
**Where:** [writer.py:10-20](../src/supernote_export/writer.py#L10-L20)
**Source:** internal `/code-review high`, gpt-5.6-sol, gemini-3.1-pro-high — repo review, 2026-08-10

### What happens

`build_markdown` drops the filename straight into the wiki-link:

```python
embed = f"![[{pdf_filename}]]\n"
```

Obsidian reads `[` and `]` as link syntax, `|` as an alias separator, and `#` as a heading
link. A name containing any of them produces an embed that points somewhere else or does not
render.

### Example scenario

You rename a note on the device to `Status #2`. The output pair is `Status #2.pdf` and
`Status #2.md`, and the Markdown holds `![[Status #2.pdf]]`. Obsidian reads that as a link to
the heading `2.pdf` inside a note called `Status `, finds nothing, and shows an unresolved
link. The PDF sits right beside it, unreachable from the note.

### Notes for a fix

Obsidian's wiki-link syntax has no escape for these characters, so the fix cannot live in the
embed. Two options, and they are not equivalent:

- **Strip or replace the characters in `naming.py`.** The embed then always works, at the
  cost of output files no longer matching the name you chose on the device — which cuts
  against the reservation rule that exists to honor exactly those names.
- **Emit a standard Markdown link, `[name](name.pdf)`**, which does support escaping. It
  always resolves, but Obsidian shows no inline PDF preview, so the note loses the "the
  original is one glance away" property the design rests on.

Pick deliberately. If naming changes, [KI-01](#ki-01) is in the same code and the two should
be planned together.

---

<a id="ki-08"></a>
## KI-08 — A page that really starts with a code fence is mangled

**Severity:** Medium
**Where:** [transcribe.py:64-72](../src/supernote_export/transcribe.py#L64-L72)
**Source:** internal `/code-review high`, gpt-5.6-sol, gemini-3.1-pro-high — repo review, 2026-08-10

### What happens

`_strip_code_fence` assumes an opening fence came from the model wrapping its answer, not
from the page itself.

```python
stripped = text.strip()
if not stripped.startswith("```"):
    return stripped
lines = stripped.splitlines()[1:]  # drop the opening fence and any language tag
if lines and lines[-1].strip() == "```":
    lines = lines[:-1]  # drop the closing fence
return "\n".join(lines).strip()
```

The opening fence is removed unconditionally. The closing one is removed only if it is the
last line. When the page genuinely starts with a fenced snippet followed by more writing, the
opener goes and the closer stays.

### Example scenario

You sketch a shell command at the top of a page, fence it, and write notes underneath. The
transcription comes back as the fenced block plus your prose. `_strip_code_fence` deletes the
opening ``` and leaves the closing one, so Obsidian reads everything *after* the closer as
the start of a new code block. The rest of the page renders as code.

### Notes for a fix

A first improvement: strip only when the last line is also a fence **and** the total fence
count is even. That fixes the case in the scenario above — a fenced snippet followed by prose
leaves an odd count, so nothing is stripped.

It is not a complete answer, and the entry should not pretend otherwise. A page that is
*entirely* one fenced block has an even count and a fence at each end, so the rule still
unwraps it and loses the block. Going the other way, a page whose own content has an unclosed
fence leaves an odd count, so a model wrapper around it is left in place. Text alone cannot
separate a wrapper the model added from markup the page really had.

So pick a position deliberately: accept the residual ambiguity with the even-count rule, which
is strictly better than today; or stop guessing and make the model's wrapper detectable —
ask for a delimiter the prompt controls, and strip only that.

`tests/test_transcribe.py` already covers the stripper. Add both the "page starts with real
fenced content" and the "whole page is one fenced block" cases as failing tests first, so the
chosen rule is pinned against the case it does not solve.

---

<a id="ki-09"></a>
## KI-09 — A missing `[transcribe]` extra fails once per note, after each PDF render

**Severity:** Medium
**Where:** [cli.py:92-97](../src/supernote_export/cli.py#L92-L97)
**Source:** gpt-5.6-sol — full-codebase review

### What happens

The CLI builds a transcriber whenever `--no-transcribe` is absent, but MLX is imported lazily
inside the transcriber's methods, so nothing checks that `mlx-vlm` is installed until the
first page of the first note.

```python
transcriber = None
if not args.no_transcribe:
    # Imported here so a --no-transcribe run never loads MLX.
    from .transcribe import MlxVlmTranscriber

    transcriber = MlxVlmTranscriber(model=args.model, page_markers=args.page_markers)
```

By then `pipeline.run` has already rendered that note's PDF. The `ModuleNotFoundError` is
caught per note, so the batch continues and repeats the whole cycle for every note.

### Example scenario

Someone installs the base package on a Mac, forgets the extra, and runs the tool over forty
notes. The tool renders forty PDFs, throws away all forty, and prints forty identical
`ModuleNotFoundError: mlx_vlm` lines. The fix — one `pip install` — is never mentioned.

### Notes for a fix

Check once in `cli.main`, before `run` is called, and exit with a message naming the install
command. `importlib.util.find_spec("mlx_vlm")` does this without importing MLX, which keeps
the lazy-import invariant intact.

Constraint: the check belongs in `cli.py`, not in `transcribe.py`. A library caller that
supplies its own `Transcriber` must not be forced to have MLX installed.

---

<a id="ki-10"></a>
## KI-10 — A bad `--input` prints a traceback

**Severity:** Medium
**Where:** [cli.py:89-109](../src/supernote_export/cli.py#L89-L109), [discover.py:19-28](../src/supernote_export/discover.py#L19-L28)
**Source:** internal `/code-review high`, gpt-5.6-sol, gemini-3.1-pro-high — repo review, 2026-08-10

### What happens

`discover_notes` raises `FileNotFoundError` or `ValueError` before the per-note error handling
in `pipeline.run` is reached, and `cli.main` wraps nothing:

```python
summary = run(
    args.input,
    args.output,
    transcriber=transcriber,
    pdf_mode=args.pdf_mode,
    max_pixels=args.max_pixels,
    overwrite=args.overwrite,
    on_progress=_print_progress,
)
_print_summary(summary)
return 1 if summary.failed else 0
```

The exception propagates out of `main` and Python prints a stack trace.

### Example scenario

You mistype the input path. Instead of `No such file or directory: /path/to/Meetings`, you
get eight frames of traceback ending in `FileNotFoundError`, with the useful line last.

### Notes for a fix

Catch `FileNotFoundError` and `ValueError` around the `run` call in `cli.main`, print one line
to stderr, and return a non-zero exit code. Keep the catch narrow — a broad `except Exception`
would also swallow bugs that should surface.

`tests/test_cli.py` covers the parser and the progress printer; the exit-code path has no
test today, which is part of [ENH-03](ENHANCEMENTS.md#enh-03).

---

<a id="ki-11"></a>
## KI-11 — Indentation on a page's first line is stripped

**Severity:** Low
**Where:** [transcribe.py:53](../src/supernote_export/transcribe.py#L53), [transcribe.py:66-72](../src/supernote_export/transcribe.py#L66-L72)
**Source:** internal `/code-review high`, gpt-5.6-sol, gemini-3.1-pro-high — repo review, 2026-08-10

### What happens

Two `strip()` calls on the way out remove leading whitespace from the first line of every
page. `assemble_transcription` does it per page:

```python
body = text.strip()
```

and `_strip_code_fence` does it again on the whole block. The prompt explicitly asks the model
to preserve indentation, so this undoes work the model did correctly.

### Example scenario

A page begins with a sub-bullet that continues a list from the previous page. The model
transcribes it with four leading spaces. Both `strip()` calls remove them, so Obsidian renders
it as a top-level bullet and the nesting is lost.

### Notes for a fix

The calls exist to detect a blank page and to trim trailing newlines, neither of which needs
leading whitespace removed. Use `strip()` for the emptiness test but keep the original text:

```python
if not text.strip():
    continue
body = text.rstrip()
```

`_strip_code_fence` needs both of its paths fixed, not just the last line. Its first statement
is `stripped = text.strip()`, and the early return hands that value straight back for every
page without a fence — which is most of them. Test the fence on a stripped copy and return the
`rstrip()`-ed original, so the early return preserves indentation too.

Low severity because it affects only the first line of a page, and only when that line is
indented. Cheap to fix while [KI-08](#ki-08) is open, since both live in the same two
functions.
