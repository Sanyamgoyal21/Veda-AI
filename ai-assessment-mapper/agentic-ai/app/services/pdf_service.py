"""
Converts PDF files into per-page raster images so they can be sent to the
vision model. Also handles plain image files (PNG/JPG) by treating them as a
single-page "document" so the rest of the pipeline is format-agnostic.
"""
import io
import os
import re
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


def has_text_layer(file_path: str) -> bool:
    """True for typed/digitally-generated PDFs where PyMuPDF can read real
    text (as opposed to a scanned image with no embedded text layer)."""
    if os.path.splitext(file_path)[1].lower() != ".pdf":
        return False
    try:
        doc = fitz.open(file_path)
        found = any(page.get_text().strip() for page in doc)
        doc.close()
        return found
    except Exception:
        return False


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(s: str) -> list[str]:
    return _TOKEN_RE.findall(s.lower())


def _find_word_span(flat_tokens: list[tuple], query_tokens: list[str], max_skip: int = 4):
    """
    Finds the best contiguous run of page words (in reading order) that
    matches `query_tokens` as an in-order subsequence, tolerating a handful
    of extra page words interspersed (e.g. a "Q1. Answer:" label the
    transcription doesn't include). Returns (start_index, end_index) into
    `flat_tokens`, inclusive, or None if no good match is found.
    """
    n, m = len(flat_tokens), len(query_tokens)
    if not n or not m:
        return None

    anchors = [i for i in range(n) if flat_tokens[i][0] == query_tokens[0]]
    best = None  # (matched_count, start, end)

    for anchor in anchors:
        pos = anchor
        matched = 1
        last_matched_pos = anchor
        qi = 1
        while qi < m and pos < n - 1:
            found = False
            for lookahead in range(1, max_skip + 2):
                if pos + lookahead >= n:
                    break
                if flat_tokens[pos + lookahead][0] == query_tokens[qi]:
                    pos += lookahead
                    last_matched_pos = pos
                    matched += 1
                    qi += 1
                    found = True
                    break
            if not found:
                qi += 1  # tolerate an unmatched query token and keep going

        if best is None or matched > best[0]:
            best = (matched, anchor, last_matched_pos)

    if best is None:
        return None

    matched, start, end = best
    if matched < max(3, int(m * 0.6)):
        return None
    return start, end


def refine_text_region(file_path: str, page_number: int, text: str) -> dict | None:
    """
    Vision models are unreliable at guessing pixel coordinates for text they
    read. For PDFs with a real text layer (typed documents, not photographed
    handwriting), we instead find the EXACT bounding box of `text` by
    aligning it word-by-word against the PDF's real word positions -
    deterministic and pixel-accurate, no guessing.

    This matches every wrapped line of a multi-line answer individually
    (rather than just its first/last line), so the resulting box correctly
    spans lines of different widths and never clips the first or last word.
    Returns a normalized region dict, or None if there's no text layer or no
    good match - callers should fall back to the model-provided box then.
    """
    if os.path.splitext(file_path)[1].lower() != ".pdf":
        return None

    query_tokens = _tokenize(text)
    if not query_tokens:
        return None

    try:
        doc = fitz.open(file_path)
        if page_number < 1 or page_number > doc.page_count:
            doc.close()
            return None

        page = doc.load_page(page_number - 1)
        page_width, page_height = page.rect.width, page.rect.height
        raw_words = page.get_text("words")  # (x0, y0, x1, y1, word, block, line, word_no)
        doc.close()
    except Exception:
        return None

    if not raw_words or not page_width or not page_height:
        return None

    raw_words.sort(key=lambda w: (w[5], w[6], w[7]))

    flat_tokens: list[tuple] = []
    for w in raw_words:
        for tok in _tokenize(w[4]):
            flat_tokens.append((tok, w))

    span = _find_word_span(flat_tokens, query_tokens)
    if span is None:
        return None

    start, end = span
    matched_words = [flat_tokens[i][1] for i in range(start, end + 1)]

    x0 = min(w[0] for w in matched_words)
    y0 = min(w[1] for w in matched_words)
    x1 = max(w[2] for w in matched_words)
    y1 = max(w[3] for w in matched_words)

    width = (x1 - x0) / page_width
    height = (y1 - y0) / page_height
    if width <= 0 or height <= 0:
        return None

    # Small padding so the box doesn't hug the glyphs too tightly, clamped
    # so it never runs past the page edge.
    pad_x, pad_y = 0.006, 0.005
    norm_x = max(0.0, x0 / page_width - pad_x)
    norm_y = max(0.0, y0 / page_height - pad_y)
    norm_width = min(1.0 - norm_x, width + 2 * pad_x)
    norm_height = min(1.0 - norm_y, height + 2 * pad_y)
    if norm_width <= 0 or norm_height <= 0:
        return None

    return {"page": page_number, "x": norm_x, "y": norm_y, "width": norm_width, "height": norm_height}
