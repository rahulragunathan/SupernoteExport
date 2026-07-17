from pathlib import Path

from supernote_export.transcribe import (
    _default_hf_home,
    _strip_code_fence,
    assemble_transcription,
)


def test_default_hf_home_resolves_under_the_current_users_home():
    """Machine-independent: no username baked into the default weights location."""
    default = _default_hf_home()
    assert Path.home() in default.parents
    assert default.name == "Local-Models"


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
