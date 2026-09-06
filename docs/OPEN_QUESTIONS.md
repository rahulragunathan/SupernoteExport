# Open Questions

Things not yet settled, decisions first. [ROADMAP.md](ROADMAP.md) carries the one-line index;
this file carries the reasoning.

These are not work items. Each is a decision waiting to be made, a gap in what the tests
prove, or a risk knowingly carried. An entry that turns out to describe defined wrong
behavior with a known fix is a bug — move it to [KNOWN_ISSUES.md](KNOWN_ISSUES.md).

Each entry has a stable ID. When one is settled it leaves this file: into the code plus a
CHANGELOG entry if it changed anything, into KNOWN_ISSUES or ENHANCEMENTS if it became work,
or into "Decisions taken and not taken" in [CLAUDE.md](../CLAUDE.md) if the answer was to do
nothing.

**IDs are assigned in ascending order and never reused**, including after an entry is
deleted. The next free ID is **UNK-07**.

Entries are ordered Decision, then Verification, then Risk, with ties broken by ascending ID.
There is no open Decision today.

## Kind

| Kind | Means |
| ---- | ----- |
| **Decision** | The code does something defensible, but nobody has chosen whether it is right. Asks for an answer. |
| **Verification** | The behavior is probably correct and nothing proves it. Asks for a test, or a deliberate acceptance. |
| **Risk** | Known, understood, accepted for now. Asks for nothing until circumstances change. |

---

<a id="unk-01"></a>

## UNK-01 — Do planned names collide under macOS case and Unicode folding?

**Kind:** Verification
**Where:** [naming.py:43-51](../src/supernote_export/naming.py#L43-L51)
**Source:** gpt-5.6-sol — full-codebase review

`plan_output_names` tracks taken names in a `set[str]` and compares them as raw Python
strings:

```python
def allocate(out_dir: str, base: str) -> str:
    used = taken.setdefault(out_dir, set())
    name = base
    occurrence = 1
    while name in used:
        occurrence += 1
        name = f"{base}-{occurrence}"
    used.add(name)
    return name
```

macOS ignores case and normalizes Unicode, so two names the allocator treats as distinct —
`Meeting` and `meeting`, or the same accented word in NFC and NFD — can name one file on
disk. The second note would then overwrite the first.

In practice the same two source notes cannot sit in one folder on this Mac's APFS volume
either, which is why this has never been observed. It would matter on a case-sensitive volume
feeding output to a case-insensitive one, or on a network share.

**What settles it:** a test that plans two names differing only by case, and two differing
only by Unicode normalization, and asserts what the allocator does. Then either accept the
result deliberately or fold the comparison — `casefold()` plus `unicodedata.normalize("NFC", …)`
on the key, keeping the original string as the name.

---

<a id="unk-02"></a>

## UNK-02 — Is a 1.5M-pixel cap safe for models other than Qwen3-VL?

**Kind:** Risk
**Where:** [convert.py:20-31](../src/supernote_export/convert.py#L20-L31)

The cap protects against an empty generation from the model. Why it is 1.5M, why the number
is hard-coded rather than read from model metadata, and the measurements behind it are the
standing rule, and they live in *Key invariants* in [CLAUDE.md](../CLAUDE.md). This entry is
only about what that rule does not cover.

It was measured against one model. Another `--model` may have a different cliff, and nothing
checks at runtime. The `vlm` eval covers only the default model, and only when it is cached.
So silent empty output on an untested model-and-cap combination is possible today, with
`--max-pixels` as the manual control.

Accepted on two grounds. The archival PDF is rendered separately at full resolution, so
nothing is lost whatever the model does. And when *every* page comes back empty the result is
an embed-only `.md`, which is obvious on opening the note.

That second ground is narrower than it looks. A cap that is wrong for a model need not fail
every page — and a single dropped page is silent, which is [KI-03](KNOWN_ISSUES.md#ki-03). The
obvious-failure argument covers the total failure, not the partial one.

**What settles it:** nothing, until the default model changes or someone reports empty output
on a different `--model`. At that point a per-model sweep is the answer, which is the
measurement side of [ENH-08](ENHANCEMENTS.md#enh-08).

---

<a id="unk-03"></a>

## UNK-03 — How stable is the `mlx-vlm` API we call?

**Kind:** Risk
**Where:** [transcribe.py:98-120](../src/supernote_export/transcribe.py#L98-L120)

`MlxVlmTranscriber` calls `load`, `load_config`, `apply_chat_template` and `generate`. Those
were pinned against mlx-vlm 0.6.5; 0.6.10 is installed today and the suite is green.
`pyproject.toml` requires only `mlx-vlm>=0.1.12`, so a future release can move them again.

We already know the API does not always mean what it appears to: `load(**kwargs)` does not
pass processor arguments through — mlx-vlm rebuilds the image processor from
`preprocessor_config.json` and discards them. That is why the pixel cap is applied before the
transcriber sees an image.

Accepted because the surface is small and isolated. Every call sits in one class in one file,
so a break stays inside `transcribe.py`, and the `Transcriber` protocol means the rest of the
pipeline does not move.

**What settles it:** nothing until an upgrade breaks. The `vlm` eval is the detector, and it
is opt-in, so the break will show up in a real run first.

---

<a id="unk-04"></a>

## UNK-04 — The `.pdf` and `.md` land as two operations, with no `fsync`

**Kind:** Risk
**Where:** [writer.py:40-70](../src/supernote_export/writer.py#L40-L70)

`write_note_outputs` stages both files under unique temporary names and renames them into
place:

```python
staged.append((_stage(pdf_path, pdf_bytes), pdf_path))
staged.append((_stage(md_path, markdown.encode("utf-8")), md_path))
for tmp, final in staged:
    os.replace(tmp, final)
```

[ARCHITECTURE.md](ARCHITECTURE.md) describes what that guarantees and the two limits it does
not — no `fsync`, and the two renames not being one transaction. This entry is about why those
limits are carried rather than closed.

The consequence that matters: an interrupted `--overwrite` can leave a new PDF beside the old
Markdown. Both files then exist, so the next run skips the note and the mismatch persists.

**A manifest was weighed and declined.** It came out of the 0.7.0 plan review as the tenth
finding: write a marker after both files land, and treat its absence as an incomplete pair.
It was not taken — that is a state file, its own staging problem, and a migration for output
already on disk, all for a gap of two operations that has never been observed.

Accepted on those terms. The window is two `os.replace` calls on files already written to
disk, and the damage is a stale `.md` next to a fresh `.pdf`, recoverable with `--overwrite`.

**What settles it:** a report of the mismatch actually happening, or a change that widens the
window — anything that puts real work between the two renames. Either would make the manifest
worth its cost.

---

<a id="unk-05"></a>

## UNK-05 — Do users know where their weights actually landed?

**Kind:** Risk
**Where:** [transcribe.py:1-8](../src/supernote_export/transcribe.py#L1-L8)

The tool sets no environment variables, so weights go wherever Hugging Face caches them:
`~/.cache/huggingface` unless the user exports `HF_HOME`. That is the right behavior — forcing
a location was tried and removed — but it is silent.

Someone who keeps models in `~/Local-Models` and never exported `HF_HOME` quietly gets a
second copy under the default cache. Hugging Face reads `HF_HOME` (or the narrower
`HF_HUB_CACHE`) and never searches for an existing tree, so weights under a path the variables
do not name are invisible to it.

The cost is disk space and a re-download, not correctness, which is why there is no runtime
check. `hf cache scan` lists what is where, and `hf cache delete` reclaims duplicates.

**What settles it:** nothing, unless the download becomes a common complaint. If it does, the
answer is a one-line note in the CLI's first-run output naming the resolved cache path, not a
tool-set variable.

---

<a id="unk-06"></a>

## UNK-06 — Can two concurrent runs publish a cross-run PDF and Markdown pair?

**Kind:** Risk
**Where:** [writer.py:40-70](../src/supernote_export/writer.py#L40-L70)
**Source:** gpt-5.6-sol — repo review, 2026-09-01
**Reconfirmed:** gpt-5.6-sol — repo review, 2026-09-01

Staging under unique temporary names solves one concurrency problem: two runs over the same
output folder cannot write to, or clean up, each other's scratch file. The comment in `_stage`
says exactly that, and it is true.

It does not make the *pair* atomic. Two runs converting the same note interleave four renames
over two final paths, and nothing orders them. One run's PDF can end up beside the other run's
Markdown. If both runs saw the same source note the two are identical and the interleaving is
harmless; if one run used `--max-pixels` or a different `--model`, they are not.

There is no lock, no generation marker, and no test covering two processes.

Accepted for now because the tool is run by hand, one invocation at a time, and the documented
use is a person converting a folder. The risk arrives with a scheduled run, a watch mode, or
anyone running two windows at once.

**What settles it:** a decision that concurrent runs are supported, which means a per-output
lock or a generation id and a test that actually runs two processes; or a decision that they
are not, which means saying so in the README and failing fast on a detectable second run. The
manifest in [UNK-04](#unk-04) would carry the generation id if that direction is taken.
