import os
import subprocess
import sys

from supernote_export.transcribe import (
    _strip_code_fence,
    assemble_transcription,
)


def test_importing_transcribe_leaves_hf_home_unset():
    """Weights land wherever Hugging Face puts them; we impose no location.

    Runs in a subprocess with ``HF_HOME`` stripped, because the import-time
    environment can only be observed on a fresh interpreter.
    """
    env = {key: value for key, value in os.environ.items() if key != "HF_HOME"}
    probe = "import supernote_export.transcribe, os; print('HF_HOME' in os.environ)"
    result = subprocess.run(
        [sys.executable, "-c", probe],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "False"


def test_strips_markdown_language_fence():
    text = "```markdown\n# Heading\n\n- a\n```"
    assert _strip_code_fence(text) == "# Heading\n\n- a"


def test_strips_bare_fence():
    assert _strip_code_fence("```\nhello\n```") == "hello"


def test_leaves_unfenced_text_untouched():
    assert _strip_code_fence("# Heading\n\n- a") == "# Heading\n\n- a"


def test_handles_opening_fence_without_closing():
    assert _strip_code_fence("```markdown\n# Heading") == "# Heading"


def test_blank_stays_blank():
    assert _strip_code_fence("   \n  ") == ""


def test_assemble_none_joins_pages_with_a_blank_line():
    assert assemble_transcription(["one", "two"], "none") == "one\n\ntwo"


def test_assemble_line_break_joins_pages_with_a_rule():
    assert assemble_transcription(["one", "two"], "line-break") == "one\n\n---\n\ntwo"


def test_assemble_page_numbers_uses_true_source_page_numbers():
    # Page 2 is blank: it is dropped but page 3 keeps its real number (gap, no renumber).
    result = assemble_transcription(["one", "", "three"], "page-numbers")
    assert result == "## Page 1\n\none\n\n## Page 3\n\nthree"


def test_assemble_drops_blank_pages_without_leaving_gaps():
    assert assemble_transcription(["", "two", "   ", "four"], "none") == "two\n\nfour"


def test_assemble_empty_when_all_pages_blank():
    assert assemble_transcription(["", "  ", "\n"], "page-numbers") == ""
