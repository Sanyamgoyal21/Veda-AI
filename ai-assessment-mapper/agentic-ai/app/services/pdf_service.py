"""
Converts PDF files into per-page raster images so they can be sent to the
vision model. Also handles plain image files (PNG/JPG) by treating them as a
single-page "document" so the rest of the pipeline is format-agnostic.
"""
import io
import os
from dataclasses import dataclass

import fitz  # PyMuPDF
from PIL import Image

PDF_RENDER_DPI = int(os.getenv("PDF_RENDER_DPI", "200"))
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


@dataclass
class PageImage:
    page: int  # 1-indexed
    image: Image.Image


def load_document_pages(file_path: str) -> list[PageImage]:
    """Return a list of PageImage for a PDF or single image file."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return _render_pdf_pages(file_path)

    if ext in IMAGE_EXTENSIONS:
        image = Image.open(file_path).convert("RGB")
        return [PageImage(page=1, image=image)]

    raise ValueError(f"Unsupported file type: {ext}")


def _render_pdf_pages(file_path: str) -> list[PageImage]:
    pages: list[PageImage] = []
    zoom = PDF_RENDER_DPI / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    try:
        doc = fitz.open(file_path)
    except Exception as exc:  # corrupted PDF
        raise ValueError(f"Could not open PDF file: {exc}") from exc

    if doc.page_count == 0:
        raise ValueError("PDF has no pages")

    for index in range(doc.page_count):
        page = doc.load_page(index)
        pix = page.get_pixmap(matrix=matrix)
        image = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
        pages.append(PageImage(page=index + 1, image=image))

    doc.close()
    return pages
