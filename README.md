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

See [ARCHITECTURE.md](ARCHITECTURE.md) for the module breakdown, a diagram, and
the design decisions behind the two independent paths.

## Requirements

- macOS on Apple Silicon (MLX is Metal-native).
- Python **3.13** (3.10–3.13 supported; **not** 3.14 yet — some deps lack wheels).
- ~35 GB free disk for the default model on first run.

Model weights download once to **`~/Local-Models`** and are cached there. Set
`HF_HOME` before running to put them somewhere else.

## Setup

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt          # runtime
pip install -r requirements-dev.txt      # + pytest, ruff (for development)
```

## Usage

```bash
# A whole folder (recursive; subfolder tree is mirrored under --output)
python -m supernote_export \
  --input  "/path/to/Supernote/Note/Meetings" \
  --output "/path/to/vault/Notes/Meetings"

# A single file
python -m supernote_export --input note.note --output ./out
```

### Options

| Flag | Default | Meaning |
|------|---------|---------|
| `--input` | *(required)* | A `.note` file or a folder (searched recursively). |
| `--output` | *(required)* | Output root; input subfolder tree is mirrored under it. |
| `--model` | `mlx-community/Qwen3-VL-30B-A3B-Instruct-8bit` | MLX-VLM model for transcription. |
| `--pdf-mode` | `raster` | `raster` (pixel-exact) or `vector` (traced/scalable). |
| `--max-pixels` | `1500000` | Cap on page-image pixels fed to the VLM. Native ~4.9M **reliably breaks** Qwen3-VL (empty output); keep this under ~2M. |
| `--page-separators` / `--no-page-separators` | off | Put a `---` rule between pages (vs. just a blank line). |
| `--no-transcribe` | off | PDF only; the `.md` holds just the embed (fast, no model). |
| `--overwrite` | off | Re-convert even if the `.md` exists (default: skip → idempotent). |

**Output naming.** A timestamp stem (`20250817_132236.note`) becomes `2025-08-17`;
a note you renamed on-device keeps its name. Same-date collisions get `-2`, `-3`.

### Alternative models

The default is tuned for messy handwriting + layout. Lighter/faster swaps:

```bash
--model mlx-community/olmOCR-7B-0725-8bit          # transcription-tuned, ~8 GB
--model mlx-community/Qwen2.5-VL-7B-Instruct-8bit  # smaller baseline
```

## Development

```bash
# Required: the integration tests convert a real .note, which isn't shipped here.
export SUPERNOTE_TEST_NOTE="/path/to/20250817_132236.note"

pytest            # deterministic layers + the real-.note integration tests
ruff format . && ruff check .
```

`SUPERNOTE_TEST_NOTE` is **required, not optional**. If it's unset or points at a
missing file, the integration tests *fail* rather than skip — they are the only
coverage of the real `supernotelib` boundary, so a silent skip would quietly
reduce the suite to mocks-testing-mocks.

> **Note:** the integration tests currently assert this specific sample's
> properties (a `2025-08-17` output stem and a 3-page count), so the variable has
> to point at `20250817_132236.note` in particular — any other note fails on those
> assertions. Replacing it with a small committed fixture note is tracked in
> [ROADMAP.md](ROADMAP.md).

The VLM boundary is a `Transcriber` protocol, so tests inject a fake and never
require the model. The transcription itself is verified manually (see the plan).
