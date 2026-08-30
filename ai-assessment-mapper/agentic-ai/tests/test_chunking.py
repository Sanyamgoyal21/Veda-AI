"""Deterministic tests for document chunking. No AI calls."""
from app.services.chunking import Chunk, chunk_pages, resolve_absolute_page
from app.services.pdf_service import PageImage


def _fake_pages(n):
    return [PageImage(page=i, image=None) for i in range(1, n + 1)]


def test_short_document_is_not_chunked():
    pages = _fake_pages(4)
    chunks = chunk_pages(pages, chunk_size=6, overlap=1)
    assert len(chunks) == 1
    assert [p.page for p in chunks[0].pages] == [1, 2, 3, 4]
    assert chunks[0].overlap_pages == set()


def test_long_document_is_chunked_with_overlap():
    pages = _fake_pages(14)
    chunks = chunk_pages(pages, chunk_size=6, overlap=1)
    assert len(chunks) > 1

    covered = set()
    for c in chunks:
        covered.update(p.page for p in c.pages)
    assert covered == set(range(1, 15)), "every page must be covered by at least one chunk"

    for i in range(len(chunks) - 1):
        a_pages = {p.page for p in chunks[i].pages}
        b_pages = {p.page for p in chunks[i + 1].pages}
        assert a_pages & b_pages, "adjacent chunks must share at least one overlap page"


def test_no_chunk_exceeds_configured_size():
    pages = _fake_pages(20)
    chunks = chunk_pages(pages, chunk_size=6, overlap=1)
    for c in chunks:
        assert len(c.pages) <= 6


def test_resolve_absolute_page_translates_chunk_relative_position():
    # Reproduces a real production bug: for a chunk covering absolute pages
    # [3, 4], the vision model reported region.page as 1 and 2 (its
    # position within the chunk) instead of the true page numbers - which
    # then made every item in that chunk look like it belonged to an
    # EARLIER, already-processed chunk once compared for page ownership,
    # silently discarding all of it (Q9/Q10's answers vanished entirely).
    chunk = Chunk(pages=[PageImage(page=3, image=None), PageImage(page=4, image=None)], overlap_pages={3})
    assert resolve_absolute_page(chunk, 1) == 3
    assert resolve_absolute_page(chunk, 2) == 4


def test_resolve_absolute_page_is_a_noop_for_the_first_chunk():
    # A document's first chunk always has position == absolute page already
    # (both start at 1), so resolving must never change anything there.
    chunk = Chunk(pages=[PageImage(page=1, image=None), PageImage(page=2, image=None)], overlap_pages=set())
    assert resolve_absolute_page(chunk, 1) == 1
    assert resolve_absolute_page(chunk, 2) == 2


def test_resolve_absolute_page_leaves_out_of_range_values_unchanged():
    chunk = Chunk(pages=[PageImage(page=5, image=None), PageImage(page=6, image=None)], overlap_pages=set())
    assert resolve_absolute_page(chunk, 5) == 5  # already absolute, out of the 1-2 relative range
    assert resolve_absolute_page(chunk, None) is None
    assert resolve_absolute_page(chunk, 0) == 0
