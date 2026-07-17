from pathlib import Path

import pytest

from supernote_sync.discover import discover_notes


def test_single_file_returns_one_entry_with_current_subdir(tmp_path):
    note = tmp_path / "20250817_132236.note"
    note.write_bytes(b"noteSN_FILE_VER_20230015")
    assert discover_notes(note) == [(note, Path("."))]


def test_single_non_note_file_raises(tmp_path):
    other = tmp_path / "thing.txt"
    other.write_text("x")
    with pytest.raises(ValueError):
        discover_notes(other)


def test_missing_path_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        discover_notes(tmp_path / "nope")


def test_folder_globs_recursively_and_mirrors_tree(tmp_path):
    (tmp_path / "20250101_000000.note").write_bytes(b"x")
    sub = tmp_path / "Level 2"
    sub.mkdir()
    (sub / "20250817_132236.note").write_bytes(b"x")
    (tmp_path / "ignore.txt").write_text("x")

    result = discover_notes(tmp_path)
    # Sorted, .note only, with parent-relative subdir preserved.
    assert result == [
        (tmp_path / "20250101_000000.note", Path(".")),
        (tmp_path / "Level 2" / "20250817_132236.note", Path("Level 2")),
    ]
