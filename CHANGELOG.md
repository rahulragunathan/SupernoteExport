# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Each released section names a development phase. The releases up to 0.7.1 were reconstructed
from the repository history when this file was created. The rule: one **minor** release per
named phase, and a **patch** release where doc-only or housekeeping work stands on its own
(0.6.1). Housekeeping commits that sit between two phases are folded into the release that
follows them, and the entry for such a commit names it inline. Each release's compare link
under `## Reference` spans exactly the commits that release describes, and is the evidence
for the reconstruction.

Versions at or below 0.7.1 have no git tag; tagging starts with the first release cut after
this file existed.

## [Unreleased]

## [0.7.3] - 2026-09-01 — Repo-wide external review

### Added

- Six known issues and one open question, from a repo-wide review by gpt-5.6-sol,
  gemini-3.1-pro-high and an internal `/code-review high`. Five of the six were reproduced by
  running them rather than by reading the code: `--no-transcribe --overwrite` destroying
  existing transcriptions, an embed-only `.md` counting as converted, outputs written mode
  0600, a progress-callback error recorded as a conversion failure, and a writer test that
  asserts the opposite of its name.

### Fixed

- `__version__` in `supernote_export/__init__.py` still read `0.1.0`. Version 0.7.2 bumped
  `pyproject.toml` alone, leaving the two disagreeing.

## [0.7.2] - 2026-09-01 — Documentation restructure

### Added

- `CHANGELOG.md`, this file.
- `docs/KNOWN_ISSUES.md`, `docs/ENHANCEMENTS.md` and `docs/OPEN_QUESTIONS.md`. Every open
  finding now carries a stable ID (`KI-nn`, `ENH-nn`, `UNK-nn`) rated on a defined scale, with
  a code excerpt, a concrete failure scenario, and notes to start work from cold.
- A "Decisions taken and not taken" section in `CLAUDE.md`, holding the ideas that were
  weighed and dropped.

### Changed

- `ARCHITECTURE.md` and `ROADMAP.md` moved into `docs/`. The only documentation left at the
  repository root is `README.md`, `CLAUDE.md`, `CHANGELOG.md` and `LICENSE`.
- `docs/ROADMAP.md` is a pointer index: three tables of ID, title and rating, with the detail
  in the supporting files. It carries only work that has not happened yet.
- Every reference that read "see the ROADMAP" now names the entry it means.

### Removed

- The ROADMAP's `Status` phase ledger, `Resolved` archive and `Notes` section. Their content
  moved: shipped work into this file, standing rules into `CLAUDE.md`, open items into the
  three supporting files.

## [0.7.1] - 2026-08-24 — Plain-English docs

### Changed

- Rewrote `README.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `CLAUDE.md` and the code comments in
  plain English, cutting jargon and hedging without dropping technical detail.

## [0.7.0] - 2026-08-18 — Output naming and skip integrity

### Fixed

- **One run could plan the same name twice.** `plan_output_names` counted base names and never
  reserved the finished ones, so a note renamed on the device to `2025-08-17-2` and a
  date-derived `2025-08-17-2` could both be planned. The second note was then skipped as done,
  or overwritten with `--overwrite`. Names now come from two passes: stems chosen on the device
  are reserved first, so a generated suffix can never take one.
- **A rerun trusted the `.md` alone.** A note whose `.pdf` was lost stayed skipped forever
  behind a broken embed. `pipeline.run` now requires both files before it skips.

### Changed

- `write_note_outputs` stages both files under unique temporary names and renames them into
  place, so a file that exists is one that was written in full. Unique names mean two runs over
  one output folder cannot clean up each other's work.
- Three writer tests exercise the staging path, and three naming tests pin the two-pass
  allocation, including the sorted order discovery really produces.

The plan for this phase was reviewed externally and returned ten findings; nine were taken,
including two passes instead of one, unique temporary filenames, and staging both files before
publishing either. The tenth proposed a manifest so both files land as one transaction. It was
declined, and the reasoning is recorded as an accepted risk in `docs/OPEN_QUESTIONS.md`.

## [0.6.1] - 2026-08-10 — Repo review and doc fixes

A full health check with no branch in flight: an internal review over `src/` and `tests/`,
plus two external reviewers. The suite was green and `ruff` clean going in. Every code finding
was filed rather than hot-fixed, because none had appeared in a real run.

### Fixed

- `tests/test_vlm_eval.py` still said `HF_HOME` is set on import of `transcribe`, which 0.6.0
  had removed.
- `ARCHITECTURE.md` claimed there is no network call at conversion time, which ignored the
  first-run weight download. Now qualified.

### Changed

- `.gitignore` ignores `.venv` without a trailing slash (`55e28c7`, folded into this
  release). With the slash the pattern matched only a directory, so this project's `.venv`
  — a symlink to an environment outside the synced folder — was never ignored.

## [0.6.0] - 2026-07-26 — Standard Hugging Face cache

### Removed

- `_default_hf_home()`, and with it the tool's habit of setting `HF_HOME` at module scope.
  Weights now go to `~/.cache/huggingface` unless the user exports `HF_HOME`, exactly as for
  any other Hugging Face tool. Setting the variable from library code imposed a non-standard
  cache and, because Hugging Face and MLX read it at import time, forced every import in the
  module below the assignment. It also carried a `RuntimeError` risk when the home directory
  could not be resolved.

### Added

- A test that starts a fresh interpreter and imports `transcribe`, proving the import leaves
  `HF_HOME` alone. Import-time environment effects only show up in a new process.

### Fixed

- `requirements-dev.txt` quoted `-e ".[dev,transcribe]"`, which pip tolerates and uv's
  requirements parser rejects. Unquoted, both accept it.

### Changed

- Documented `uv venv --python 3.13` as the way to rebuild the environment. Homebrew's
  `python@3.13` can disappear, which breaks a venv whose interpreter is gone; uv supplies its
  own build without adding a second CPython to the Homebrew tree.

## [0.5.0] - 2026-07-19 — Page markers and progress output

### Added

- `--page-markers {none,line-break,page-numbers}`, replacing `--page-separators`. Page numbers
  follow the real source page, so a blank page leaves a gap in the headings instead of
  renumbering the rest, and the headings stay lined up with the embedded PDF.
- `pipeline.run` takes an `on_progress(index, total, path, status)` callback, and the CLI
  prints one line per note to stderr. The library still prints nothing.
- A deterministic cap test in `note_to_page_images`.

### Changed

- The page-joining logic moved into `assemble_transcription`, a pure function with unit tests.
- **The `max_pixels` investigation, tried and reverted.** The pre-render downscale was first
  swapped for the model processor's own `max_pixels` argument. The eval passed, which was false
  confidence: mlx-vlm rebuilds the image processor from `preprocessor_config.json` and discards
  the argument, so the real cap stayed at the model default of 16.7M pixels. A real note then
  produced an embed-only `.md`, and instrumenting the boundary proved it. The pre-render cap was
  restored.

  Whether the safe cap can be read from model metadata was checked at the same time. It cannot:
  the safe point sits below everything the model advertises. 1.5M works, while 2.0M, 2.36M
  (`num_position_embeddings × (patch·merge)²`) and 16.7M (`size.longest_edge`) all return empty
  output. The deterministic cap test is now the primary guard, because the eval can pass by luck.
- The eval's anchor matching became case-insensitive.
- `.gitignore` ignores `*.code-workspace` (`50ce0dc`, folded into this release).

## [0.4.0] - 2026-07-17 — Packaging and MIT license

### Added

- A `supernote-export` console script.
- An MIT license, bundled into the wheel.

### Changed

- Moved to a `src/` layout built by hatchling. The package is not importable from the repository
  root, so tests exercise the installed artifact and a packaging bug fails the suite instead of
  hiding behind a working-directory import.
- Dependencies live only in `pyproject.toml`; the `requirements*.txt` files are thin pointers.
- `mlx-vlm` became the optional `[transcribe]` extra, so the base PDF-only install works on any
  platform. This mirrors the lazy MLX import.
- `.gitignore` ignores the packaging build artifacts: `/dist/`, `/build/`, `*.egg-info/`.
- Restructured `ROADMAP.md` into fixed sections and aligned the phase entries on "Done"
  (`0a8e496`, folded into this release).

## [0.3.0] - 2026-07-17 — Test fixture and VLM eval

### Added

- A sample `.note` committed at `tests/fixtures/20260717_012708.note`, so the integration tests
  convert a real file through real `supernotelib` anywhere the repository is checked out, with no
  setup. A `.gitignore` negation ships this one sample while blocking any other `.note` dropped
  into that folder.
- An opt-in eval, `tests/test_vlm_eval.py`, marked `vlm` and deselected by default. It runs the
  real model on the fixture and asserts tolerant properties — output is not empty, and a few
  clearly printed anchors appear — rather than an exact transcription.

### Removed

- `SUPERNOTE_TEST_NOTE`. It read like "point this at any note", but the tests assert one sample's
  name and page count, so any other note failed with a confusing error. The committed fixture
  replaced it, and the assertions now describe a file the repository owns.

## [0.2.0] - 2026-07-17 — Post-rename cleanup

### Changed

- Renamed the repository to SupernoteExport and the package to `supernote_export`.
- Removed machine-specific paths.
- `build_architecture.py` looked up its own `<diagram>` element instead of using the variable two
  lines above. Refactored; the generated file stayed identical.
- Dropped a hand-counted test number from the documentation. It had drifted twice, so it was
  removed rather than updated.

### Added

- `ARCHITECTURE.md` and its generated diagram, built by `docs/architecture/build_architecture.py`
  rather than drawn by hand.

### Fixed

- `CLAUDE.md` said the integration test skips when the sample is absent. It fails loudly.
- `CLAUDE.md` did not mention `ARCHITECTURE.md`, or that the diagram is generated.

## [0.1.0] - 2026-07-17 — Conversion pipeline

### Added

- The whole tool: a `.note` file becomes an archival PDF plus a Markdown note whose body is a
  local vision-language-model transcription, with the PDF embedded at the bottom. One pair per
  note, with the input subfolder tree mirrored under `--output`.
- Transcription on a local MLX-VLM model, defaulting to
  `mlx-community/Qwen3-VL-30B-A3B-Instruct-8bit`. No cloud, no API keys.
- `--input`, `--output`, `--model`, `--pdf-mode`, `--max-pixels`, `--no-transcribe` and
  `--overwrite`.

### Fixed

- **The vision-language model has a resolution cliff.** The first real batch produced empty
  transcriptions for five notes out of seven. Image size was the cause. A measured sweep on a
  failing page gave reliable output at or below 1.77M pixels and empty output at or above 2.76M;
  a full Supernote page is about 4.9M. `note_to_page_images` now shrinks pages to `--max-pixels`,
  default 1.5M, before the model sees them.

### Removed

- `--image-scale`, replaced by `--max-pixels`. Scale was the wrong control: the failure depends
  on the pixel count, so that is what the flag now caps.

### Notes

- **Runtime validation, 2026-07-17.** The first conversion of a real folder ran clean, which
  settled the open question of whether the default model handles real handwriting. Two lighter
  alternatives stay documented in the README, `olmOCR-7B-0725-8bit` and
  `Qwen2.5-VL-7B-Instruct-8bit`.

## Reference

[Unreleased]: https://github.com/rahulragunathan/SupernoteExport/compare/v0.7.3...main
[0.7.3]: https://github.com/rahulragunathan/SupernoteExport/compare/v0.7.2...v0.7.3
[0.7.2]: https://github.com/rahulragunathan/SupernoteExport/compare/4372a6a...v0.7.2
[0.7.1]: https://github.com/rahulragunathan/SupernoteExport/compare/9572966...4372a6a
[0.7.0]: https://github.com/rahulragunathan/SupernoteExport/compare/f7946e3...9572966
[0.6.1]: https://github.com/rahulragunathan/SupernoteExport/compare/2c73227...f7946e3
[0.6.0]: https://github.com/rahulragunathan/SupernoteExport/compare/50ce0dc...2c73227
[0.5.0]: https://github.com/rahulragunathan/SupernoteExport/compare/0a8e496...50ce0dc
[0.4.0]: https://github.com/rahulragunathan/SupernoteExport/compare/d193422...0a8e496
[0.3.0]: https://github.com/rahulragunathan/SupernoteExport/compare/b92adc8...d193422
[0.2.0]: https://github.com/rahulragunathan/SupernoteExport/compare/75e455e...b92adc8
[0.1.0]: https://github.com/rahulragunathan/SupernoteExport/tree/75e455e
