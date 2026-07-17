"""Local handwriting transcription via an MLX vision-language model.

The transcriber sits behind the ``Transcriber`` protocol so the pipeline (and its
tests) depend only on ``transcribe_pages``; the concrete ``MlxVlmTranscriber`` is
the MLX-VLM implementation. Model weights are placed by ``HF_HOME``, which is set
before any Hugging Face / mlx-vlm import runs (see ``_default_hf_home``).
"""

from __future__ import annotations

import os
from pathlib import Path


def _default_hf_home() -> Path:
    """Where model weights land when ``HF_HOME`` isn't already set."""
    return Path.home() / "Local-Models"


# Both libraries read HF_HOME at import time, so this must run before either is
# imported. Respects an existing override if present.
os.environ.setdefault("HF_HOME", str(_default_hf_home()))

import tempfile  # noqa: E402
from typing import Protocol, runtime_checkable  # noqa: E402

from PIL import Image  # noqa: E402

DEFAULT_MODEL = "mlx-community/Qwen3-VL-30B-A3B-Instruct-8bit"
PAGE_SEPARATOR = "\n\n---\n\n"  # a horizontal rule between pages
PLAIN_SEPARATOR = "\n\n"  # just a blank line between pages

PROMPT = (
    "You are transcribing one page of handwritten notes.\n"
    "Reproduce the page as GitHub-flavored Markdown, preserving its layout and "
    "structure: headings, bullet and numbered lists, checkboxes, indentation, "
    "tables, and columns.\n"
    "Transcribe the text exactly as written. Do not summarize, correct, "
    "translate, rephrase, or invent any content.\n"
    "For any word or mark you genuinely cannot read, write [?].\n"
    "If the page is blank, output nothing at all.\n"
    "Output only the transcription itself — no preamble, no commentary, and do "
    "not wrap it in a Markdown code fence."
)


def _strip_code_fence(text: str) -> str:
    """Remove an outer ``` / ```markdown fence the model may add despite the prompt."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()[1:]  # drop the opening fence (and any language tag)
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]  # drop the closing fence
    return "\n".join(lines).strip()


@runtime_checkable
class Transcriber(Protocol):
    """Anything that can turn a note's page images into Markdown text."""

    def transcribe_pages(self, images: list[Image.Image]) -> str: ...


class MlxVlmTranscriber:
    """Transcribe pages with an MLX vision-language model (default Qwen3-VL)."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 4096,
        page_separators: bool = False,
    ) -> None:
        self.model_name = model
        self.max_tokens = max_tokens
        self._separator = PAGE_SEPARATOR if page_separators else PLAIN_SEPARATOR
        self._model = None
        self._processor = None
        self._config = None

    def _ensure_loaded(self) -> None:
        if self._model is None:
            from mlx_vlm import load
            from mlx_vlm.utils import load_config

            self._model, self._processor = load(self.model_name)
            self._config = load_config(self.model_name)

    def _transcribe_one(self, image_path: str) -> str:
        from mlx_vlm import generate
        from mlx_vlm.prompt_utils import apply_chat_template

        formatted = apply_chat_template(self._processor, self._config, PROMPT, num_images=1)
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

    def transcribe_pages(self, images: list[Image.Image]) -> str:
        self._ensure_loaded()
        transcriptions: list[str] = []
        # mlx-vlm reads images from paths; write each page to a scratch file.
        with tempfile.TemporaryDirectory() as tmp:
            for index, image in enumerate(images):
                page_path = Path(tmp) / f"page_{index}.png"
                image.convert("RGB").save(page_path)
                transcriptions.append(self._transcribe_one(str(page_path)))
        # Drop blank pages so they don't create empty gaps between pages.
        return self._separator.join(t for t in transcriptions if t.strip())
