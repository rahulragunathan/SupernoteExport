# ROADMAP

**What's next.** This file holds only work that has not happened yet, at index level. It does
not describe what shipped or how the code works today.

| Looking for | Read |
|-------------|------|
| Detail on an open bug | [KNOWN_ISSUES.md](KNOWN_ISSUES.md) |
| Detail on a candidate enhancement | [ENHANCEMENTS.md](ENHANCEMENTS.md) |
| Detail on an open question | [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) |
| What already shipped | [CHANGELOG.md](../CHANGELOG.md) |
| How the code works now | [README.md](../README.md), [ARCHITECTURE.md](ARCHITECTURE.md), [CLAUDE.md](../CLAUDE.md) |
| Ideas considered and dropped | "Decisions taken and not taken" in [CLAUDE.md](../CLAUDE.md) |

The tables below are **pointers, not summaries** — ID, title, rating, link. Nothing is
described twice.

An item's whole life is a move: it enters here and its supporting file together, and on
completion is deleted from both, with the record written into CHANGELOG `[Unreleased]`. An
item dropped rather than built moves to "Decisions taken and not taken". IDs are never
reused. Nothing here looks backward — completed phases are CHANGELOG releases.

**Last Updated**: 2026-09-01 (restructured into the pointer index plus three supporting files)

## Status

The tool is in daily use. The open queue is weighted toward silent-failure paths — output
that looks complete and is not — and none of it has been seen in a real run. Nothing is
scheduled.

### Phases

No phase is in flight. The next one is a full external code review of the codebase; its
findings will be filed here.

## Known Issues

Most severe first. Severity definitions and full detail in [KNOWN_ISSUES.md](KNOWN_ISSUES.md).

| ID | Issue | Severity |
|----|-------|----------|
| [KI-01](KNOWN_ISSUES.md#ki-01) | Output names shift between runs, so a note is skipped or written twice | Critical |
| [KI-02](KNOWN_ISSUES.md#ki-02) | A stray PDF with no matching `.md` is overwritten without `--overwrite` | Critical |
| [KI-03](KNOWN_ISSUES.md#ki-03) | A dropped page is indistinguishable from a blank page | High |
| [KI-04](KNOWN_ISSUES.md#ki-04) | A page that hits the token cap is written out as finished | High |
| [KI-05](KNOWN_ISSUES.md#ki-05) | Installing on Python 3.14 fails halfway instead of being refused | Medium |
| [KI-06](KNOWN_ISSUES.md#ki-06) | A half-loaded model poisons every later note in the batch | Medium |
| [KI-07](KNOWN_ISSUES.md#ki-07) | `[`, `]`, `\|` and `#` in a name break the Obsidian embed | Medium |
| [KI-08](KNOWN_ISSUES.md#ki-08) | A page that really starts with a code fence is mangled | Medium |
| [KI-09](KNOWN_ISSUES.md#ki-09) | A missing `[transcribe]` extra fails once per note, after each PDF render | Medium |
| [KI-10](KNOWN_ISSUES.md#ki-10) | A bad `--input` prints a traceback | Medium |
| [KI-11](KNOWN_ISSUES.md#ki-11) | Indentation on a page's first line is stripped | Low |

## Enhancements

Highest priority first. Priority definitions and full detail in [ENHANCEMENTS.md](ENHANCEMENTS.md).

| ID | Enhancement | Priority | Effort |
|----|-------------|----------|--------|
| [ENH-01](ENHANCEMENTS.md#enh-01) | Load each notebook once instead of twice per note | Medium | ~2 hours |
| [ENH-02](ENHANCEMENTS.md#enh-02) | Validate options at the library seam, not just in argparse | Medium | ~3 hours |
| [ENH-03](ENHANCEMENTS.md#enh-03) | Fill the test gaps: failure recovery, CLI exit codes, vector PDF | Medium | ~half a day |
| [ENH-04](ENHANCEMENTS.md#enh-04) | Make the `vlm` eval's cache check honest | Medium | ~2 hours |
| [ENH-05](ENHANCEMENTS.md#enh-05) | Optional YAML front matter for Dataview | Medium | ~half a day |
| [ENH-06](ENHANCEMENTS.md#enh-06) | Stream page images instead of building them all | Medium | ~3 hours |
| [ENH-07](ENHANCEMENTS.md#enh-07) | Skip directories named `*.note` during discovery | Medium | ~1 hour |
| [ENH-08](ENHANCEMENTS.md#enh-08) | Model comparison harness over real pages | Low | ~1 day |
| [ENH-09](ENHANCEMENTS.md#enh-09) | Drop the `Operating System :: MacOS` classifier | Low | ~15 minutes |
| [ENH-10](ENHANCEMENTS.md#enh-10) | Share the fixture constants through `tests/conftest.py` | Low | ~1 hour |

## Open Questions

Decisions first, then verification gaps, then accepted risks. Kind definitions and the
reasoning behind each in [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).

| ID | Question | Kind |
|----|----------|------|
| [UNK-01](OPEN_QUESTIONS.md#unk-01) | Do planned names collide under macOS case and Unicode folding? | Verification |
| [UNK-02](OPEN_QUESTIONS.md#unk-02) | Is a 1.5M-pixel cap safe for models other than Qwen3-VL? | Risk |
| [UNK-03](OPEN_QUESTIONS.md#unk-03) | How stable is the `mlx-vlm` API we call? | Risk |
| [UNK-04](OPEN_QUESTIONS.md#unk-04) | The `.pdf` and `.md` land as two operations, with no `fsync` | Risk |
| [UNK-05](OPEN_QUESTIONS.md#unk-05) | Do users know where their weights actually landed? | Risk |
