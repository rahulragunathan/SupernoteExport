from pathlib import Path

from supernote_export.naming import derive_name, plan_output_names


def test_derive_name_parses_supernote_timestamp():
    assert derive_name("20250817_132236") == "2025-08-17"


def test_derive_name_keeps_renamed_stem_verbatim():
    assert derive_name("Level 2 - Coaching Recap") == "Level 2 - Coaching Recap"


def test_derive_name_keeps_almost_timestamp_that_does_not_match():
    # Wrong length / shape must fall through to verbatim, not misparse.
    assert derive_name("2025-08-17") == "2025-08-17"
    assert derive_name("20250817") == "20250817"


def test_plan_output_names_no_collision():
    out = Path("/out")
    planned = plan_output_names([(Path("/in/20250817_132236.note"), out)])
    assert planned == [(Path("/in/20250817_132236.note"), out, "2025-08-17")]


def test_plan_output_names_disambiguates_same_date_deterministically():
    out = Path("/out")
    entries = [
        (Path("/in/20250817_132236.note"), out),
        (Path("/in/20250817_181500.note"), out),
        (Path("/in/20250817_090000.note"), out),
    ]
    names = [name for _, _, name in plan_output_names(entries)]
    assert names == ["2025-08-17", "2025-08-17-2", "2025-08-17-3"]


def test_plan_output_names_disambiguation_is_scoped_per_directory():
    entries = [
        (Path("/in/a/20250817_132236.note"), Path("/out/a")),
        (Path("/in/b/20250817_090000.note"), Path("/out/b")),
    ]
    names = [name for _, _, name in plan_output_names(entries)]
    # Same date in different output dirs must NOT collide.
    assert names == ["2025-08-17", "2025-08-17"]
