"""
Splits a document's pages into overlapping chunks so a single vision call
never has to hold an entire long document in context at once.

Why this exists: with the whole document sent in one request, the model can
confuse two structurally-similar multi-part questions that are many pages
apart (e.g. a probability question numbered 21(i)/(ii) getting mixed up with
an unrelated geometry question numbered 26(i)/(ii)/(iii) several pages
later) - this was observed as a real failure during development, not a
hypothetical. Chunking bounds how much a single call can "see" at once,
which structurally prevents far-apart questions from ever being confused for
each other, since they're never in the same request.

Short documents never get chunked: if the whole document already fits in one
chunk, behavior and cost are byte-for-byte identical to the pre-chunking
implementation.
"""
import os
from dataclasses import dataclass

from app.services.pdf_service import PageImage

CHUNK_SIZE = int(os.getenv("EXTRACTION_CHUNK_SIZE", "3"))
CHUNK_OVERLAP = int(os.getenv("EXTRACTION_CHUNK_OVERLAP", "1"))


@dataclass
class Chunk:
    pages: list[PageImage]
    # 1-indexed page numbers in this chunk that a neighboring chunk also sees.
    overlap_pages: set


def chunk_pages(pages: list[PageImage], chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[Chunk]:
    if len(pages) <= chunk_size:
        return [Chunk(pages=pages, overlap_pages=set())]

    step = max(1, chunk_size - overlap)
    chunks: list[Chunk] = []
    n = len(pages)
    start = 0

    while start < n:
        end = min(start + chunk_size, n)
        window = pages[start:end]

        overlap_pages = set()
        if start > 0:
            overlap_pages.update(p.page for p in window[:overlap])
        if end < n:
            overlap_pages.update(p.page for p in window[-overlap:])

        chunks.append(Chunk(pages=window, overlap_pages=overlap_pages))

        if end >= n:
            break
        start += step

    return chunks


def resolve_absolute_page(chunk: Chunk, reported_page: int | None) -> int | None:
    """
    The vision model is unreliable about whether a region's reported `page`
    means the document's real page number or just the 1-indexed position of
    that image within THIS chunk's request - confirmed as a real,
    reproducible failure (not a hypothetical): a chunk covering absolute
    pages [3, 4] came back reporting "page": 1 and "page": 2 for that
    content, silently discarding every item once the page-ownership check
    compared that against the WRONG chunk. Resolve using the chunk's own
    known page list, which is always authoritative, rather than trusting
    the model's number outright.

    If `reported_page` is a valid 1-indexed position within this chunk,
    translate it to that position's real absolute page number (a no-op
    whenever they already coincide, e.g. a document's first chunk, where
    position and absolute page are identical). A value outside that range
    can't be a within-chunk position, so it's returned unchanged - already
    absolute, or invalid in a way remapping can't fix anyway.
    """
    if not reported_page or not (1 <= reported_page <= len(chunk.pages)):
        return reported_page
    return chunk.pages[reported_page - 1].page
