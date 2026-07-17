from pathlib import Path

import pytest

from supernote_export.cli import _print_progress, build_parser


def _parse(*argv):
    return build_parser().parse_args(["--input", "in", "--output", "out", *argv])


def test_page_markers_defaults_to_none():
    assert _parse().page_markers == "none"


def test_page_markers_accepts_the_three_modes():
    for mode in ("none", "line-break", "page-numbers"):
        assert _parse("--page-markers", mode).page_markers == mode


def test_page_markers_rejects_unknown_mode():
    with pytest.raises(SystemExit):
        _parse("--page-markers", "heading")


def test_old_page_separators_flag_is_gone():
    with pytest.raises(SystemExit):
        _parse("--page-separators")


def test_print_progress_convert_line(capsys):
    _print_progress(1, 3, Path("/notes/a.note"), "convert")
    assert capsys.readouterr().err.strip() == "[1/3] Converting a.note"


def test_print_progress_skip_line(capsys):
    _print_progress(2, 3, Path("/notes/b.note"), "skip")
    assert capsys.readouterr().err.strip() == "[2/3] Skipping b.note (exists)"
