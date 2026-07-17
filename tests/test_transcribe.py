from pathlib import Path

from supernote_export.transcribe import _default_hf_home, _strip_code_fence


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
