"""
Deterministic tests for the cross-chunk deduplication/merge logic that lets
question and answer extraction split a long document into chunks without
losing or duplicating content. No AI calls - these operate on raw dicts
shaped like what a chunk's extraction call would return.
"""
from app.agents.answer_extraction_agent import _dedupe_and_merge_answers
from app.agents.question_extraction_agent import _dedupe_across_chunks, _split_bundled_subparts


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
