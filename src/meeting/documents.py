"""Attachments as text the summary can cite (D22, D23): a PDF or DOCX in, numbered blocks out.

    DOCX  Docling (docling-slim, its simple pipeline: no models) -> Markdown -> blocks "agenda.docx #3"
    PDF   the text layer, page by page, with pypdfium2 (PDFium) -> blocks "brief.pdf p2.1"

Why not Docling for PDF too: its PDF pipeline runs a layout model on PyTorch (or on onnxruntime-gpu, which can't sit
next to the onnxruntime faster-whisper uses), about a gigabyte more in the Function for page layout an agenda
rarely needs. A PDF without a text layer (a scan) is kept with no blocks and a warning; reading it is OCR, for
Document Intelligence on Azure later.

Every attachment is untrusted, like the transcript: the checks before reading are size, page count and, for a
DOCX, what the ZIP holds (no ZIP bomb, a Word document and nothing else). The blocks go to the model inside
<attachment> blocks that their own text cannot close (summarize.py).
"""

import json
import re
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol

BLOCK_MAX_CHARS = 1200  # a longer paragraph or table is split at line ends
DOCX_MAX_UNCOMPRESSED = 50 * 1024 * 1024
DOCX_MAX_MEMBERS = 2000
DOCX_REQUIRED = ("[Content_Types].xml", "word/document.xml")
_IMAGE = re.compile(r"<!--\s*image\s*-->")


class AttachmentRejected(ValueError):
    """The attachment cannot be read. `code` is the job's error code (D16); the message names the file and the
    limit, never the content."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Block:
    ref: str  # what the summary cites: "agenda.docx #3", "brief.pdf p2.1"
    text: str


@dataclass(frozen=True)
class Document:
    name: str
    kind: str  # pdf | docx
    pages: int | None  # None for DOCX: Word computes pages when it lays the document out, the file has none
    blocks: list[Block]
    engine: str
    warnings: list[str] = field(default_factory=list)

    @property
    def chars(self) -> int:
        return sum(len(b.text) for b in self.blocks)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2) + "\n"

    @classmethod
    def from_json(cls, text: str) -> "Document":
        data = json.loads(text)
        data["blocks"] = [Block(**b) for b in data["blocks"]]
        return cls(**data)


class DocumentReader(Protocol):
    """A file and its checked kind in, a Document out. Local: LocalReader; Azure: Document Intelligence later."""

    def read(self, path: Path, name: str, kind: str) -> Document: ...


def split_long(text: str, limit: int = BLOCK_MAX_CHARS) -> list[str]:
    """A block of at most `limit` characters per piece, cut at line ends (or hard, for one endless line)."""
    pieces, current = [], ""
    for line in text.splitlines():
        while len(line) > limit:
            if current:
                pieces.append(current)
                current = ""
            pieces.append(line[:limit])
            line = line[limit:]
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit:
            pieces.append(current)
            current = line
        else:
            current = candidate
    if current.strip():
        pieces.append(current)
    return [p.strip() for p in pieces if p.strip()]


def markdown_blocks(markdown: str) -> list[str]:
    """Paragraphs, headings, list items and tables of a Markdown text, each split to BLOCK_MAX_CHARS."""
    text = _IMAGE.sub("", markdown)
    out = []
    for paragraph in re.split(r"\n\s*\n", text):
        out.extend(split_long(paragraph.strip()))
    return out


def check_docx(path: Path) -> None:
    """A DOCX is a ZIP: refuse one that is not a Word document, is encrypted, or unpacks to far more than it is."""
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
    except (zipfile.BadZipFile, OSError):
        raise AttachmentRejected("unreadable_attachment", f"{path.name} is not a readable ZIP file") from None
    names = {m.filename for m in members}
    if not all(r in names for r in DOCX_REQUIRED):
        raise AttachmentRejected("unsupported_type", f"{path.name} is a ZIP file but not a Word document")
    if len(members) > DOCX_MAX_MEMBERS:
        raise AttachmentRejected(
            "too_large", f"{path.name} holds {len(members)} files, the limit is {DOCX_MAX_MEMBERS}"
        )
    if any(m.flag_bits & 0x1 for m in members):
        raise AttachmentRejected("unreadable_attachment", f"{path.name} is encrypted")
    unpacked = sum(m.file_size for m in members)
    if unpacked > DOCX_MAX_UNCOMPRESSED:
        limit = DOCX_MAX_UNCOMPRESSED // (1024 * 1024)
        raise AttachmentRejected("too_large", f"{path.name} unpacks to {unpacked} bytes, the limit is {limit} MB")


class LocalReader:
    """Docling for DOCX, pypdfium2 for PDF. Both import on first use: only jobs with attachments need them."""

    def __init__(self, max_pages: int = 50) -> None:
        self.max_pages = max_pages
        self._converter = None

    def read(self, path: Path, name: str, kind: str) -> Document:
        if kind == "docx":
            return self._docx(path, name)
        if kind == "pdf":
            return self._pdf(path, name)
        raise AttachmentRejected("unsupported_type", f"{name}: no reader for {kind}")

    def _docx(self, path: Path, name: str) -> Document:
        check_docx(path)
        from docling.datamodel.base_models import ConversionStatus, InputFormat
        from docling.document_converter import DocumentConverter

        if self._converter is None:
            self._converter = DocumentConverter(allowed_formats=[InputFormat.DOCX])
        try:
            result = self._converter.convert(path, raises_on_error=False)
        except Exception:  # Docling wraps parser errors in several types; any of them means the same here
            raise AttachmentRejected("unreadable_attachment", f"{name} could not be read as a Word document") from None
        if result.status not in (ConversionStatus.SUCCESS, ConversionStatus.PARTIAL_SUCCESS):
            raise AttachmentRejected("unreadable_attachment", f"{name} could not be read as a Word document")
        texts = markdown_blocks(result.document.export_to_markdown())
        warnings = [] if texts else [f"{name}: no text"]
        blocks = [Block(ref=f"{name} #{i}", text=t) for i, t in enumerate(texts, start=1)]
        return Document(name=name, kind="docx", pages=None, blocks=blocks, engine="docling docx", warnings=warnings)

    def _pdf(self, path: Path, name: str) -> Document:
        import pypdfium2 as pdfium

        try:
            pdf = pdfium.PdfDocument(str(path))
        except pdfium.PdfiumError:
            raise AttachmentRejected(
                "unreadable_attachment", f"{name} could not be opened (damaged or encrypted)"
            ) from None
        try:
            pages = len(pdf)
            if pages > self.max_pages:
                raise AttachmentRejected("too_large", f"{name} has {pages} pages, the limit is {self.max_pages}")
            blocks = []
            for number in range(1, pages + 1):
                page = pdf[number - 1]
                textpage = page.get_textpage()
                text = textpage.get_text_bounded().replace("\r\n", "\n").replace("\r", "\n")
                textpage.close()
                page.close()
                # PDFium gives one line per text line and no paragraph marks: blocks are runs of lines, cut at line
                # ends, each joined into one line for the prompt.
                pieces = [" ".join(p.split()) for p in split_long(text)]
                blocks += [Block(ref=f"{name} p{number}.{i}", text=t) for i, t in enumerate(pieces, start=1)]
        finally:
            pdf.close()
        warnings = [] if blocks else [f"{name}: no text layer (a scan?), nothing to read without OCR"]
        return Document(name=name, kind="pdf", pages=pages, blocks=blocks, engine="pypdfium2 text", warnings=warnings)
