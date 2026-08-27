"""Deterministic tests for document chunking. No AI calls."""
from app.services.chunking import chunk_pages
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
