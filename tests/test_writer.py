from supernote_sync.writer import build_markdown, write_note_outputs


def test_build_markdown_transcription_on_top_embed_on_bottom():
    md = build_markdown("# Heading\n\n- a point", "2025-08-17.pdf")
    assert md == "# Heading\n\n- a point\n\n![[2025-08-17.pdf]]\n"


def test_build_markdown_without_transcription_is_embed_only():
    md = build_markdown("", "2025-08-17.pdf")
    assert md == "![[2025-08-17.pdf]]\n"


def test_build_markdown_strips_trailing_whitespace_from_transcription():
    md = build_markdown("text\n\n\n", "n.pdf")
    assert md == "text\n\n![[n.pdf]]\n"


def test_write_note_outputs_creates_dir_and_both_files(tmp_path):
    out_dir = tmp_path / "Comedy" / "Level 2"
    pdf_path, md_path = write_note_outputs(
        out_dir, "2025-08-17", b"%PDF-1.4 fake", "body\n\n![[2025-08-17.pdf]]\n"
    )
    assert pdf_path == out_dir / "2025-08-17.pdf"
    assert md_path == out_dir / "2025-08-17.md"
    assert pdf_path.read_bytes() == b"%PDF-1.4 fake"
    assert md_path.read_text(encoding="utf-8") == "body\n\n![[2025-08-17.pdf]]\n"
