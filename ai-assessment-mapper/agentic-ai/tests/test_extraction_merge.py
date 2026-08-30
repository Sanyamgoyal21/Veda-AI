"""
Deterministic tests for the cross-chunk deduplication/merge logic that lets
question and answer extraction split a long document into chunks without
losing or duplicating content. No AI calls - these operate on raw dicts
shaped like what a chunk's extraction call would return.
"""
from unittest.mock import patch

from app.agents.answer_extraction_agent import _dedupe_and_merge_answers, _extract_raw_items
from app.agents.question_extraction_agent import _dedupe_across_chunks, _split_bundled_subparts
from app.services.pdf_service import PageImage


def test_bare_question_with_roman_subparts_is_split():
    parts = _split_bundled_subparts({
        "number": "Q21",
        "text": "Two dice are thrown. Find probability that (i) sum is 7, (ii) sum is prime.",
        "page": 2,
    })
    assert [p["number"] for p in parts] == ["21(i)", "21(ii)"]
    assert all("Two dice are thrown" in p["text"] for p in parts)


def test_repeated_number_in_unrelated_regions_is_not_merged():
    items = [
        {"detected_question_number": "28(iii)", "text": "ladder", "confidence": .8,
         "_chunk_index": 0, "regions": [{"page": 1, "x": .1, "y": .1, "width": .3, "height": .1}]},
        {"detected_question_number": "28(iii)", "text": "median", "confidence": .9,
         "_chunk_index": 0, "regions": [{"page": 1, "x": .1, "y": .7, "width": .3, "height": .1}]},
    ]
    merged, _ = _dedupe_and_merge_answers(items)
    assert len(merged) == 2


def test_question_overlap_duplicate_keeps_most_complete():
    items = [
        {"number": "11(a)", "text": "Explain mitosis.", "page": 6, "marks": 3},
        {"number": "11(a)", "text": "Explain mitosis in detail with a labelled diagram.", "page": 6, "marks": 3},
        {"number": "12", "text": "Explain meiosis.", "page": 7, "marks": 3},
    ]
    deduped, warnings = _dedupe_across_chunks(items)
    assert len(deduped) == 2
    kept = next(d for d in deduped if d["number"] == "11(a)")
    assert kept["text"] == "Explain mitosis in detail with a labelled diagram."
    assert len(warnings) == 1


def test_answer_pure_overlap_duplicate_deduped_not_doubled():
    items = [
        {
            "detected_question_number": "5",
            "text": "The answer is X.",
            "confidence": 0.9,
            "regions": [{"page": 6, "x": 0.1, "y": 0.1, "width": 0.5, "height": 0.1}],
        },
        {
            "detected_question_number": "5",
            "text": "The answer is X.",
            "confidence": 0.85,
            "regions": [{"page": 6, "x": 0.1, "y": 0.1, "width": 0.5, "height": 0.1}],
        },
    ]
    merged, _ = _dedupe_and_merge_answers(items)
    assert len(merged) == 1
    assert len(merged[0]["regions"]) == 1  # not doubled
    assert merged[0]["confidence"] == 0.85  # conservative: min of the two


def test_answer_genuine_continuation_across_chunk_boundary_fully_recovered():
    """
    The pathological case: an answer spans 3 physical pages, straddling a
    chunk boundary such that neither chunk alone sees all 3 pages. The merge
    must recover the full page span from the union of both partial views,
    not silently drop either end.
    """
    items = [
        {
            "detected_question_number": "7",
            "text": "The process starts with photosynthesis in chloroplasts.",
            "confidence": 0.9,
            "regions": [
                {"page": 5, "x": 0.1, "y": 0.1, "width": 0.5, "height": 0.2},
                {"page": 6, "x": 0.1, "y": 0.1, "width": 0.5, "height": 0.1},
            ],
        },
        {
            "detected_question_number": "7",
            "text": "The products are glucose and oxygen.",
            "confidence": 0.85,
            "regions": [
                {"page": 6, "x": 0.1, "y": 0.1, "width": 0.5, "height": 0.1},
                {"page": 7, "x": 0.1, "y": 0.2, "width": 0.6, "height": 0.15},
            ],
        },
    ]
    merged, warnings = _dedupe_and_merge_answers(items)
    assert len(merged) == 1
    pages = sorted({r["page"] for r in merged[0]["regions"]})
    assert pages == [5, 6, 7]
    assert "photosynthesis" in merged[0]["text"]
    assert "glucose" in merged[0]["text"]
    assert len(warnings) == 1


def test_chunk_relative_page_numbers_do_not_cause_wholesale_loss():
    """
    Reproduces a real production failure end-to-end: for a chunk covering
    absolute pages [3, 4], the vision model reported region.page as 1 and 2
    (its own position within that request) instead of 3 and 4. Before the
    fix, comparing that against the page-ownership map (built from real
    absolute pages) made the item look like it belonged to an earlier,
    already-owned chunk, and it was silently discarded - which is exactly
    how a real answer sheet lost every answer on its last page with no
    error or warning at all.
    """
    pages = [PageImage(page=i, image=None) for i in range(1, 5)]  # chunk_size=3 -> chunks [1,2,3] and [3,4]

    def fake_extraction(*, pages: list[PageImage], **_):
        chunk_page_numbers = [p.page for p in pages]
        if chunk_page_numbers == [1, 2, 3]:
            return {"segments": [{
                "detected_question_number": "1", "text": "answer one", "segment_type": "ANSWER_START",
                "question_number_confidence": 1, "segment_confidence": 1, "continuation_likely": False,
                "continuation_confidence": 0, "visual_order": 1, "has_diagram": False, "has_handwriting": True,
                "region": {"page": 1, "x": .1, "y": .1, "width": .5, "height": .1},
            }]}
        # The chunk covering absolute pages [3, 4] - the model reports its
        # own position within THIS request (1, 2), not the true pages.
        return {"segments": [{
            "detected_question_number": "2", "text": "answer two", "segment_type": "ANSWER_START",
            "question_number_confidence": 1, "segment_confidence": 1, "continuation_likely": False,
            "continuation_confidence": 0, "visual_order": 1, "has_diagram": False, "has_handwriting": True,
            "region": {"page": 2, "x": .1, "y": .1, "width": .5, "height": .1},  # really absolute page 4
        }]}

    with patch("app.services.vision_service.run_structured_extraction", side_effect=fake_extraction):
        items, warnings = _extract_raw_items(pages)

    numbers = {item["detected_question_number"] for item in items}
    assert numbers == {"1", "2"}, "the second chunk's item must survive, not be silently discarded"
    second = next(item for item in items if item["detected_question_number"] == "2")
    assert second["region"]["page"] == 4, "the model's chunk-relative page must resolve to the true absolute page"
    assert warnings == []


def test_unrelated_answers_are_never_merged():
    items = [
        {"detected_question_number": "1", "text": "Answer one.", "confidence": 0.9,
         "regions": [{"page": 1, "x": 0.1, "y": 0.1, "width": 0.5, "height": 0.1}]},
        {"detected_question_number": "2", "text": "Answer two.", "confidence": 0.9,
         "regions": [{"page": 1, "x": 0.1, "y": 0.3, "width": 0.5, "height": 0.1}]},
    ]
    merged, warnings = _dedupe_and_merge_answers(items)
    assert len(merged) == 2
    assert warnings == []
