# ROADMAP — SupernoteSync

## Status

**Phase 1 — Ad-hoc conversion pipeline: implemented.**
`.note` → PDF + transcribed Markdown, one pair per note, local MLX-VLM transcription,
mirrored subfolder output. 17 tests green (deterministic layers + real-`.note` integration).

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

- Reading `.note` files from Google Drive File Stream is slow (on-demand download); a slow
  folder run is Drive I/O, not a conversion bug.
- Python 3.14 unsupported (dependency wheels); pinned to 3.13.
- PySN intentionally not used; supernotelib covers all conversion needs.

## Review findings (end-of-phase)

To be completed after the first real transcription run and a `/code-review` + `/simplify`
pass. Trivial/safe fixes applied in-phase; anything larger recorded here.
