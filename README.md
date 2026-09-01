# SupernoteExport

Convert Supernote `.note` files into **Obsidian-ready PDFs and locally transcribed
Markdown**, entirely offline on your Mac.

For each `.note` file you get two files side by side:

- a **PDF** that keeps the original handwritten layout, and
- a **Markdown** note whose body is a transcription of the handwriting, with the
  PDF embedded at the bottom (`![[<name>.pdf]]`).

A local **vision-language model** does the transcription, running on MLX. No cloud,
no API keys. The embedded PDF is always the source of truth, so any transcription
error is one glance from the original.

## How it works

```text
.note ──┬── PdfConverter  → <name>.pdf   (raster by default; the source of truth)
        └── ImageConverter → page PNGs → MLX-VLM → transcription ─┐
                                                                  ▼
                                          <name>.md  = transcription + ![[<name>.pdf]]
```

- **Conversion:** [`supernotelib`](https://pypi.org/project/supernotelib/).
- **Transcription:** [`mlx-vlm`](https://github.com/Blaizzy/mlx-vlm), default model
  `mlx-community/Qwen3-VL-30B-A3B-Instruct-8bit`. Change it with `--model`.

[ARCHITECTURE.md](docs/ARCHITECTURE.md) covers the modules, a diagram, and how the two
independent paths — archival PDF and transcription — fit together.

## Requirements

- Python **3.10 to 3.13**. 3.13 is recommended, and 3.14 does not work because the
  dependencies have no wheels for it.
- **Transcription** needs macOS on Apple Silicon, because MLX runs on Metal, plus
  about 35 GB of free disk for the default model on the first run. PDF-only
  conversion (`--no-transcribe`) runs anywhere.

Model weights download once into the Hugging Face cache at
**`~/.cache/huggingface`** and are reused from there. To keep them somewhere else,
export `HF_HOME` as you would for any other Hugging Face tool, for example
`export HF_HOME=~/Local-Models` in your shell profile. This tool never sets that
variable itself.

## Install

```bash
# PDF-only conversion (any platform):
pip install "git+https://github.com/rahulragunathan/SupernoteExport.git"

# With local handwriting transcription (Apple Silicon):
pip install "supernote-export[transcribe] @ git+https://github.com/rahulragunathan/SupernoteExport.git"
```

You get a `supernote-export` command. `mlx-vlm` is the optional `[transcribe]`
extra, so the base install stays small and works on any platform.

### From a clone (development)

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,transcribe]"   # editable install, dev and transcription extras
```

No 3.13 interpreter on your PATH? [uv](https://docs.astral.sh/uv/) supplies one
without installing another system Python:

```bash
uv venv --python 3.13 .venv
uv pip install -e .[dev,transcribe]
```

## Usage

```bash
# A whole folder, searched recursively. The subfolder tree is mirrored under --output.
supernote-export \
  --input  "/path/to/Supernote/Note/Meetings" \
  --output "/path/to/vault/Notes/Meetings"

# A single file
supernote-export --input note.note --output ./out
```

`python -m supernote_export …` does the same thing if you prefer the module form.

### Options

| Flag | Default | What it does |
| --- | --- | --- |
| `--input` | *(required)* | A `.note` file, or a folder searched recursively. |
| `--output` | *(required)* | Output root. The input subfolder tree is mirrored under it. |
| `--model` | `mlx-community/Qwen3-VL-30B-A3B-Instruct-8bit` | MLX-VLM model used for transcription. |
| `--pdf-mode` | `raster` | `raster` is pixel-exact, `vector` traces the strokes into scalable paths. |
| `--max-pixels` | `1500000` | Caps the page images sent to the model. Pages are shrunk to fit first. The default is tuned for reliable transcription — read [ARCHITECTURE.md](docs/ARCHITECTURE.md) before raising it. |
| `--page-markers` | `none` | How pages are separated in the transcription: `none` is a blank line, `line-break` is a `---` rule, and `page-numbers` adds `## Page N` headings that match the PDF's page numbers. |
| `--no-transcribe` | off | PDF only. The `.md` holds just the embed. Fast, and no model needed. |
| `--overwrite` | off | Convert a note again even when its outputs exist. By default a note is skipped when both its `.md` and `.pdf` are there, so reruns are cheap. |

**Output naming.** A timestamp stem such as `20250817_132236.note` becomes
`2025-08-17`. A note you renamed on the device always keeps that
name, because those names are reserved before any date-derived name is handed out.
Whatever is still competing for one name gets `-2`, then `-3`, in the order the
notes are read.

**Progress.** Each note prints a line to stderr as it is processed
(`[3/12] Converting …`), followed by a summary at the end.

### Other models

The default is tuned for messy handwriting and layout. Lighter, faster options:

```bash
--model mlx-community/olmOCR-7B-0725-8bit          # transcription-tuned, about 8 GB
--model mlx-community/Qwen2.5-VL-7B-Instruct-8bit  # smaller baseline
```

## Development

```bash
pytest            # deterministic layers plus the real .note integration tests
ruff format . && ruff check .

pytest -m vlm     # opt-in: real transcription of the fixture, needs the model
```

The default suite needs no setup. Its integration tests convert a committed sample
note (`tests/fixtures/20260717_012708.note`) through real `supernotelib`, so the
conversion boundary is exercised anywhere the repo is checked out. The sample is
disposable and holds no personal content, and a `.gitignore` rule stops any *other*
`.note` dropped into `tests/fixtures/` from being committed by accident.

The model sits behind a `Transcriber` protocol, so the default tests inject a fake
and never load it. The real model is covered by an **opt-in eval** (`pytest -m vlm`,
deselected by default). It transcribes the fixture and checks that the output is not
empty and carries a few clearly printed anchors. Those checks are deliberately
tolerant: they guard the image-resolution cliff described in
[ARCHITECTURE.md](docs/ARCHITECTURE.md) without pinning an exact transcription.
The eval skips itself when the model config is not cached. That gate is not
airtight: a partly cached model can still start a download, which is
[ENH-04](docs/ENHANCEMENTS.md#enh-04).
