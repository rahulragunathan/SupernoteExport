# SupernoteExport

Convert Supernote `.note` files into **Obsidian-ready PDFs and locally-transcribed
Markdown** — entirely offline on your Mac.

For each `.note` file, SupernoteExport produces two side-by-side outputs:

- a **PDF** that preserves the original handwritten layout, and
- a **Markdown** note whose body is a machine-readable transcription of the
  handwriting, with the PDF embedded at the bottom (`![[<name>.pdf]]`).

Handwriting is transcribed by a local **vision-language model** (MLX, Apple-Silicon
native) — no cloud, no API keys. The embedded PDF is always the source of truth, so
any transcription error is one glance away from the original.

## How it works

```
.note ──┬── PdfConverter  → <name>.pdf   (raster by default; the source of truth)
        └── ImageConverter → page PNGs → MLX-VLM → transcription ─┐
                                                                  ▼
                                          <name>.md  = transcription + ![[<name>.pdf]]
```

- **Conversion:** [`supernotelib`](https://pypi.org/project/supernotelib/).
- **Transcription:** [`mlx-vlm`](https://github.com/Blaizzy/mlx-vlm), default model
  `mlx-community/Qwen3-VL-30B-A3B-Instruct-8bit` (swappable via `--model`).

See [ARCHITECTURE.md](ARCHITECTURE.md) for the module breakdown, a diagram, and how
the two independent paths (archival PDF and transcription) fit together.

## Requirements

- Python **3.10–3.13** (3.13 recommended).
- **Transcription** needs macOS on Apple Silicon (MLX is Metal-native) and ~35 GB
  free disk for the default model on first run. PDF-only conversion
  (`--no-transcribe`) runs anywhere.

Model weights download once into the standard Hugging Face cache
(**`~/.cache/huggingface`**) and are reused from there. To keep them elsewhere, export
`HF_HOME` as with any other Hugging Face tool — e.g. `export HF_HOME=~/Local-Models`
in your shell profile. This tool imposes no location of its own.

## Install

```bash
# PDF-only conversion (any platform):
pip install "git+https://github.com/rahulragunathan/SupernoteExport.git"

# With local handwriting transcription (Apple Silicon):
pip install "supernote-export[transcribe] @ git+https://github.com/rahulragunathan/SupernoteExport.git"
```

Installs a `supernote-export` command. `mlx-vlm` is an optional `[transcribe]`
extra, so the base install stays platform-independent and small.

### From a clone (development)

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,transcribe]"   # editable install + dev/transcription extras
```

No 3.13 interpreter on PATH? [uv](https://docs.astral.sh/uv/) supplies one without
installing another system Python:

```bash
uv venv --python 3.13 .venv
uv pip install -e .[dev,transcribe]
```

## Usage

```bash
# A whole folder (recursive; subfolder tree is mirrored under --output)
supernote-export \
  --input  "/path/to/Supernote/Note/Meetings" \
  --output "/path/to/vault/Notes/Meetings"

# A single file
supernote-export --input note.note --output ./out
```

(Equivalent to `python -m supernote_export …` if you prefer the module form.)

### Options

| Flag | Default | Meaning |
| --- | --- | --- |
| `--input` | *(required)* | A `.note` file or a folder (searched recursively). |
| `--output` | *(required)* | Output root; input subfolder tree is mirrored under it. |
| `--model` | `mlx-community/Qwen3-VL-30B-A3B-Instruct-8bit` | MLX-VLM model for transcription. |
| `--pdf-mode` | `raster` | `raster` (pixel-exact) or `vector` (traced/scalable). |
| `--max-pixels` | `1500000` | Cap on page-image pixels fed to the VLM (pages are downscaled to fit before transcription). The default is tuned for reliable transcription; see [ARCHITECTURE.md](ARCHITECTURE.md) before raising it. |
| `--page-markers` | `none` | Page separation in the transcription: `none` (blank line), `line-break` (`---` rule), or `page-numbers` (`## Page N` headers, aligned to the PDF's page numbers). |
| `--no-transcribe` | off | PDF only; the `.md` holds just the embed (fast, no model). |
| `--overwrite` | off | Re-convert even if the `.md` exists (default: skip → idempotent). |

**Output naming.** A timestamp stem (`20250817_132236.note`) becomes `2025-08-17`;
a note you renamed on-device keeps its name. Same-date collisions get `-2`, `-3`.

**Progress.** During a run, a per-note line (`[3/12] Converting …`) is printed to
stderr as each note is processed, followed by the final summary.

### Alternative models

The default is tuned for messy handwriting + layout. Lighter/faster swaps:

```bash
--model mlx-community/olmOCR-7B-0725-8bit          # transcription-tuned, ~8 GB
--model mlx-community/Qwen2.5-VL-7B-Instruct-8bit  # smaller baseline
```

## Development

```bash
pytest            # deterministic layers + the real-.note integration tests
ruff format . && ruff check .

pytest -m vlm     # opt-in: real transcription of the fixture (needs the model)
```

No setup needed for the default suite — the integration tests convert a committed
sample note (`tests/fixtures/20260717_012708.note`) through real `supernotelib`, so
the conversion boundary is genuinely exercised anywhere the repo is checked out. The
sample is disposable and carries no personal content; a `.gitignore` rule keeps any
*other* `.note` dropped in `tests/fixtures/` from being committed by accident.

The VLM boundary is a `Transcriber` protocol, so the default tests inject a fake and
never load the model. The real model is covered by an **opt-in eval** (`pytest -m vlm`, deselected by default) that transcribes the fixture and asserts the output is
non-empty and carries a few clearly-printed anchors — tolerant checks that guard the
image-resolution cliff (see [ARCHITECTURE.md](ARCHITECTURE.md)) without pinning an
exact transcription. It skips automatically if the model isn't cached.
