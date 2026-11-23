"""Attachments into text blocks (D22): real DOCX and PDF files made here, and the checks before reading them."""

import zipfile

import pytest
from docx import Document as WordDocument
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from meeting import documents
from meeting.documents import AttachmentRejected, Block, Document, LocalReader, markdown_blocks, split_long


def make_docx(path, *paragraphs, table=None):
    doc = WordDocument()
    doc.add_heading("Agenda", level=1)
    for p in paragraphs:
        doc.add_paragraph(p)
    if table:
        t = doc.add_table(rows=len(table), cols=len(table[0]))
        for r, row in enumerate(table):
            for c, value in enumerate(row):
                t.cell(r, c).text = value
    doc.save(path)
    return path


def make_pdf(path, *pages):
    pdf = canvas.Canvas(str(path), pagesize=A4)
    for lines in pages:
        y = 800
        for line in lines:
            pdf.drawString(72, y, line)
            y -= 16
        pdf.showPage()
    pdf.save()
    return path


@pytest.fixture(scope="module")
def reader():
    return LocalReader(max_pages=3)


def test_a_docx_becomes_numbered_blocks(tmp_path, reader):
    path = make_docx(
        tmp_path / "agenda.docx", "1. Launch date.", "2. Budget.", table=[["Item", "Owner"], ["Icons", "Lina"]]
    )
    doc = reader.read(path, "agenda.docx", "docx")
    assert (doc.kind, doc.pages, doc.engine, doc.warnings) == ("docx", None, "docling docx", [])
    assert [b.ref for b in doc.blocks] == ["agenda.docx #1", "agenda.docx #2", "agenda.docx #3", "agenda.docx #4"]
    assert doc.blocks[0].text == "## Agenda"  # Word's Heading 1, as Docling 2.151 writes it
    assert doc.blocks[1].text == "1. Launch date."
    assert "| Icons" in doc.blocks[3].text and "Lina" in doc.blocks[3].text  # the table stays one block
    assert doc.chars == sum(len(b.text) for b in doc.blocks)


def test_a_pdf_becomes_blocks_per_page(tmp_path, reader):
    path = make_pdf(tmp_path / "budget.pdf", ["Campaign budget", "Ads: 4,000 dinars"], ["Page two", "Total: 8,500"])
    doc = reader.read(path, "budget.pdf", "pdf")
    assert (doc.kind, doc.pages, doc.engine) == ("pdf", 2, "pypdfium2 text")
    assert [(b.ref, b.text) for b in doc.blocks] == [
        ("budget.pdf p1.1", "Campaign budget Ads: 4,000 dinars"),
        ("budget.pdf p2.1", "Page two Total: 8,500"),
    ]


def test_a_pdf_without_text_is_kept_with_a_warning(tmp_path, reader):
    path = make_pdf(tmp_path / "scan.pdf", [])
    doc = reader.read(path, "scan.pdf", "pdf")
    assert doc.blocks == [] and doc.pages == 1
    assert doc.warnings == ["scan.pdf: no text layer (a scan?), nothing to read without OCR"]


def test_too_many_pages(tmp_path, reader):
    path = make_pdf(tmp_path / "long.pdf", *[["page"]] * 4)
    with pytest.raises(AttachmentRejected) as caught:
        reader.read(path, "long.pdf", "pdf")
    assert (caught.value.code, caught.value.message) == ("too_large", "long.pdf has 4 pages, the limit is 3")


def test_a_damaged_pdf(tmp_path, reader):
    path = tmp_path / "broken.pdf"
    path.write_bytes(b"%PDF-1.7\nthis is not a pdf body")
    with pytest.raises(AttachmentRejected, match="unreadable_attachment"):
        reader.read(path, "broken.pdf", "pdf")


def test_a_zip_that_is_not_a_word_document(tmp_path, reader):
    path = tmp_path / "photos.docx"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("photo.jpg", b"\xff\xd8")
    with pytest.raises(AttachmentRejected) as caught:
        reader.read(path, "photos.docx", "docx")
    assert caught.value.code == "unsupported_type"


def test_a_zip_bomb_is_refused_before_reading(tmp_path, reader, monkeypatch):
    path = make_docx(tmp_path / "big.docx", "x" * 5000)
    monkeypatch.setattr(documents, "DOCX_MAX_UNCOMPRESSED", 1000)
    with pytest.raises(AttachmentRejected, match=r"too_large: big\.docx unpacks to"):
        reader.read(path, "big.docx", "docx")


def test_not_a_zip(tmp_path, reader):
    path = tmp_path / "fake.docx"
    path.write_bytes(b"PK\x03\x04 then nothing a ZIP needs")
    with pytest.raises(AttachmentRejected, match="unreadable_attachment"):
        reader.read(path, "fake.docx", "docx")


def test_blocks_are_split_at_line_ends():
    text = "\n".join(f"line {i:03d} " + "x" * 90 for i in range(30))  # 30 lines of 99 characters
    pieces = split_long(text, limit=500)
    assert all(len(p) <= 500 for p in pieces) and len(pieces) == 6
    assert "\n".join(pieces) == text
    assert split_long("y" * 1100, limit=500) == ["y" * 500, "y" * 500, "y" * 100]  # one endless line: hard cuts


def test_markdown_blocks_drop_image_placeholders():
    assert markdown_blocks("# Title\n\n<!-- image -->\n\nText.\n\n\n") == ["# Title", "Text."]


def test_json_round_trip():
    doc = Document("a.pdf", "pdf", 1, [Block("a.pdf p1.1", "Hello")], "pypdfium2 text", ["w"])
    assert Document.from_json(doc.to_json()) == doc


def test_an_encrypted_docx_is_refused_before_reading(tmp_path, reader):
    path = make_docx(tmp_path / "locked.docx", "Secret agenda")
    data = bytearray(path.read_bytes())
    with zipfile.ZipFile(path) as archive:
        start = archive.start_dir  # the central directory: where infolist() reads each member's flags
    at = data.find(b"PK\x01\x02", start)
    data[at + 8] |= 0x1  # general purpose bit 0 of the first member: "encrypted"
    path.write_bytes(bytes(data))
    with pytest.raises(AttachmentRejected, match=r"unreadable_attachment: locked\.docx is encrypted"):
        reader.read(path, "locked.docx", "docx")
