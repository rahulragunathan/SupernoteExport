# Architecture — SupernoteExport

SupernoteExport is a single-process CLI. It reads Supernote `.note` files and
writes two files per note: an **archival PDF** and a **Markdown note** whose body
is a local vision-language-model transcription of the handwriting, with the PDF
embedded at the bottom.

Everything runs on your Mac. There is no server, no queue, and no database. The
only network call is the first transcription run, which downloads the model
weights into the Hugging Face cache. After that, conversion works offline.

![SupernoteExport architecture](architecture/supernote-export-architecture.png)

## The shape of the system

The design is a straight pipeline with one deliberate fork. `pipeline.run()` plans
the whole batch first — discover, then name — and then loops over the notes. For
each note, `convert.py` renders the same source twice, in two independent ways:

| Path | Renderer | Resolution | Who reads it |
| ---- | -------- | ---------- | ------------ |
| PDF | `supernotelib.PdfConverter` | Full, about 4.9M px per page | Embedded in the `.md` as the archival record |
| Page images | `supernotelib.ImageConverter` | Capped at `--max-pixels`, default 1.5M | The model, which transcribes them |

**The two paths never meet.** The model never reads the PDF, and the PDF is never
downscaled. The cap is applied by shrinking the PNG before any model touches it,
so it works for any model and does not depend on one processor's internals.

That split is what lets the transcription be lossy but useful while the embedded
PDF stays pixel-exact. Any transcription error is one glance from the original,
which is also why the cap can be aggressive without hurting the archive.

## Modules

Each module does one job. Apart from `pipeline`, none of them knows about the
others.

| Module | Job |
| ------ | --- |
| `cli.py` / `__main__.py` | argparse entry point. Builds a transcriber unless `--no-transcribe`, then calls `pipeline.run()`. |
| `discover.py` | Turn `--input`, a file or a folder, into sorted `(note_path, relative_subdir)` pairs. The subdir is what mirrors the input tree under `--output`. |
| `naming.py` | Work out each output name. A `YYYYMMDD_HHMMSS` stem becomes `YYYY-MM-DD`; any other stem is kept as it is. Two notes that want one name in a folder get `-2`/`-3`. |
| `convert.py` | Wrap `supernotelib`: `note_to_pdf()` and `note_to_page_images()`. Owns the pixel cap. |
| `transcribe.py` | The `Transcriber` protocol, the pure `assemble_transcription()` that joins pages, and the `MlxVlmTranscriber` implementation. |
| `writer.py` | Compose the Markdown, transcription on top and `![[embed]]` at the bottom, then write both files. |
| `pipeline.py` | Drive the rest, catch per-note failures, and return a `Summary`. |

## Design decisions worth knowing

**Transcription sits behind a protocol.** `pipeline` depends only on
`transcribe_pages(images) -> str`. So the integration test injects a fake and
still exercises the real `supernotelib` path without loading a multi-gigabyte
model. It is also the seam for swapping in a different model or backend.

**MLX is imported inside `MlxVlmTranscriber` methods**, not at module scope. So
`--no-transcribe` runs and the default test suite never load MLX; `pytest -m vlm`
is the one exception, and it loads the real model on purpose. That is also what
lets `mlx-vlm` be the optional `[transcribe]` extra instead of a hard dependency,
which keeps the base install working on any platform.

**The weights location is not ours to choose.** `transcribe.py` sets no
environment variables, so weights land in the standard Hugging Face cache at
`~/.cache/huggingface`. `HF_HOME` moves them, exactly as it does for every other
Hugging Face tool.

**Naming is worked out, not looked up.** `plan_output_names()` runs two passes.
The first reserves the stems you chose on the device. The second hands out
date-derived names around them. So a name you picked is never taken by a generated
suffix, whatever order the notes arrive in. Nothing reads the disk, and the result
depends only on input order, so a rerun produces the same names. That is what keeps
skip-on-rerun and `--overwrite` stable.

Names hold **within** a run. Two runs that see different notes still hand out
different names, which is [KI-01](KNOWN_ISSUES.md#ki-01).

**One bad note cannot stop a batch.** `pipeline.run()` wraps each note in
`try/except`, records the failure in `Summary.failed`, and carries on. The CLI
exits non-zero if anything failed, after printing every failure.

**The page-image cap is about correctness, not speed.** Above roughly 2M pixels the
Qwen3-VL vision stack sometimes returns an *empty* generation, which silently
produces embed-only Markdown. Measured on a failing page: reliable at or below
1.77M px, empty at or above 2.0M. The 1.5M default sits below that boundary, so do
not raise it toward 2M.

`note_to_page_images` shrinks each page before the model sees it. That is a
pre-render cap, so it works for any model rather than relying on one model's
processor internals. The default is a hard-coded conservative number on purpose:
it cannot be derived from model metadata, because the cliff sits *below* every
capacity the model declares. Its `size.longest_edge` is 16.7M and its
`num_position_embeddings` math implies about 2.36M, and both return empty output.

## Data flow

```text
.note ──┬── note_to_pdf()        → PDF bytes (full resolution) ──────────┐
        │                                                                 ▼
        └── note_to_page_images() → PNGs (≤ --max-pixels) → VLM → text → writer
                                                                          │
                                                        <name>.pdf  ◄─────┤
                                                        <name>.md   ◄─────┘
```

Skip logic runs before any conversion. If both `<name>.md` and `<name>.pdf` exist
and you did not pass `--overwrite`, the note is recorded as skipped and neither
renderer runs. Requiring both is what stops a lost PDF from leaving a broken embed
for good.

`write_note_outputs` stages each file under a unique temporary name and renames it
into place. So a file that exists is one that was written in full, which is what
makes "it exists" a sound stand-in for "it was converted". Two limits: this is not
a durability guarantee, since there is no `fsync`, and the two renames are not one
transaction. [UNK-04](OPEN_QUESTIONS.md#unk-04) records both as accepted risks.

## Testing strategy

The deterministic layers are unit-tested: `discover`, `naming`, `writer`,
`convert`'s downscaler and page cap, `transcribe`'s `assemble_transcription` and
fence stripper, and the `cli` parser and progress printer. One test starts a
subprocess to check that importing `transcribe` leaves `HF_HOME` alone, because
import-time environment effects only show up in a fresh interpreter.

`pipeline` has an integration test that converts a committed sample `.note`
(`tests/fixtures/20260717_012708.note`) through real `supernotelib`, faking only
the `Transcriber`. Shipping the fixture means this coverage of the real
`supernotelib` boundary runs anywhere with no setup, and the fixture's timestamp
name doubles as coverage of `naming.py`'s date conversion. A `.gitignore` negation
commits this one sample while blocking any other `.note` in that folder.

The model itself has no unit test, by design: its output varies and it needs a
large download. Instead there is an **opt-in eval** (`tests/test_vlm_eval.py`,
marked `vlm`, deselected by default). It runs the real model on the fixture through
the whole pipeline and asserts tolerant properties — output is not empty, and a few
clearly printed anchors appear — rather than an exact transcription. It guards the
resolution cliff described above, whose signature is a silently empty, embed-only
`.md`. It skips when the model config is not in the cache. That gate is not airtight —
a partly cached model can still start a download, which is
[ENH-04](ENHANCEMENTS.md#enh-04).

Beyond the eval, the model is checked by running it and reading the result.

## Regenerating the diagram

The diagram is generated, not drawn by hand, so it round-trips without diff churn:

```bash
python docs/architecture/build_architecture.py
python ~/.claude/skills/drawio/scripts/validate.py docs/architecture/supernote-export-architecture.drawio
python ~/.claude/skills/drawio/scripts/render_png.py docs/architecture/supernote-export-architecture.drawio
mv docs/architecture/supernote-export-architecture.drawio.png docs/architecture/supernote-export-architecture.png
```

Edit `build_architecture.py`, not the `.drawio` XML. It documents its reserved
routing corridors at the top. The validator checks geometry only, so look at the
rendered PNG as well after moving boxes — a clean validation does not mean the
result reads well.
