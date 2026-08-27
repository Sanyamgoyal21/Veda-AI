"""
Mapping agent tests covering the full priority ladder plus every edge case
from the test plan (out-of-order, duplicates, unmatched, unanswered,
sub-parts, multi-page). Level 4 (semantic) is exercised with the vision
call mocked, since it's the only level that ever makes an AI call - no live
API key is needed to run this suite.
"""
from unittest.mock import patch

import pytest

from app.agents import mapping_agent
from app.schemas.answer_schema import Answer, AnswerRegion
from app.schemas.question_schema import Question
from app.utils.normalization import normalize_question_number


def q(number, text, page=1, order=1, marks=None):
    return Question(number=number, normalized_number=normalize_question_number(number),
                     text=text, page=page, order=order, marks=marks)


def a(detected, text, confidence=0.9, regions=None):
    regions = regions or [{"page": 1, "x": 0.1, "y": 0.1, "width": 0.5, "height": 0.1}]
    return Answer(
        detected_question_number=detected,
        normalized_question_number=normalize_question_number(detected),
        text=text,
        confidence=confidence,
        regions=[AnswerRegion(**r) for r in regions],
    )


def mapping_for(mappings, question_number):
    return next((m for m in mappings if m.question_number == question_number), None)


def test_exact_match():
    mappings = mapping_agent.run([q("1", "What is gravity?")], [a("1", "Gravity pulls things down.")])
    m = mapping_for(mappings, "1")
    assert m.match_level == "exact"
    assert m.match_score == 1.0


def test_normalized_match_variants():
    questions = [q("11(a)", "Explain mitosis.")]
    answers = [a("Q11 (a)", "Mitosis is cell division.")]
    mappings = mapping_agent.run(questions, answers)
    m = mapping_for(mappings, "11(a)")
    assert m.match_level == "normalized"
    assert m.match_score == 0.9


def test_fuzzy_match_for_poor_handwriting_noise():
    """
    Simulates a handwriting-recognition slip: the model misread "12(a)" as
    "12(4)" (a common a/4 confusion). Constructed with normalized_number set
    directly since real-world normalization already resolves most textual
    variants to identical keys - this tests the fuzzy tier itself, not
    normalization.
    """
    question = Question(number="12(a)", normalized_number="12(a)", text="Explain photosynthesis.",
                         page=1, order=1)
    answer = Answer(detected_question_number="12(4)", normalized_question_number="12(4)",
                     text="Photosynthesis converts light to chemical energy.", confidence=0.7,
                     regions=[AnswerRegion(page=1, x=0.1, y=0.1, width=0.5, height=0.1)])

    mappings = mapping_agent.run([question], [answer], enable_semantic=False)
    m = mapping_for(mappings, "12(a)")
    assert m is not None
    assert m.match_level == "fuzzy"
    assert 0.7 < m.match_score < 0.9


def test_out_of_order_answers_still_match_by_number_not_position():
    questions = [q("1", "Q1 text", page=1, order=1), q("2", "Q2 text", page=2, order=2), q("3", "Q3 text", page=3, order=3)]
    answers = [a("3", "Answer to 3", regions=[{"page": 2, "x": 0.1, "y": 0.1, "width": 0.5, "height": 0.1}]),
               a("1", "Answer to 1", regions=[{"page": 6, "x": 0.1, "y": 0.1, "width": 0.5, "height": 0.1}]),
               a("2", "Answer to 2", regions=[{"page": 4, "x": 0.1, "y": 0.1, "width": 0.5, "height": 0.1}])]
    mappings = mapping_agent.run(questions, answers)
    assert mapping_for(mappings, "1").answer.text == "Answer to 1"
    assert mapping_for(mappings, "2").answer.text == "Answer to 2"
    assert mapping_for(mappings, "3").answer.text == "Answer to 3"


def test_unanswered_question_produces_explicit_mapping():
    mappings = mapping_agent.run([q("1", "Q1"), q("2", "Q2")], [a("1", "Answer to 1")])
    m = mapping_for(mappings, "2")
    assert m.match_level == "unanswered"
    assert m.answer is None


def test_duplicate_answers_for_same_question_first_wins_second_reported_unmatched():
    """
    Two distinct answer entries both claiming question '1' (e.g. the student
    wrote it twice, or a genuine extraction duplicate slipped through) must
    never both silently attach to the same question - one wins, the other is
    explicitly surfaced as unmatched rather than silently dropped.
    """
    mappings = mapping_agent.run(
        [q("1", "Q1 text")],
        [a("1", "First attempt"), a("1", "Second attempt")],
        enable_semantic=False,
    )
    matched = [m for m in mappings if m.match_level not in ("unanswered", "unmatched")]
    unmatched = [m for m in mappings if m.match_level == "unmatched"]
    assert len(matched) == 1
    assert len(unmatched) == 1
    # No question was ever mapped twice.
    mapped_numbers = [m.question_number for m in matched]
    assert len(mapped_numbers) == len(set(mapped_numbers))


def test_unmatched_answer_produces_explicit_mapping():
    mappings = mapping_agent.run([q("1", "Q1")], [a("1", "Answer to 1"), a("99", "Stray answer")], enable_semantic=False)
    unmatched = [m for m in mappings if m.match_level == "unmatched"]
    assert len(unmatched) == 1
    assert unmatched[0].answer.detected_question_number == "99"


def test_subparts_11a_11b_map_independently():
    questions = [q("11(a)", "Part a"), q("11(b)", "Part b")]
    answers = [a("11(a)", "Answer a"), a("11(b)", "Answer b")]
    mappings = mapping_agent.run(questions, answers)
    assert mapping_for(mappings, "11(a)").answer.text == "Answer a"
    assert mapping_for(mappings, "11(b)").answer.text == "Answer b"


def test_multi_letter_roman_numeral_subparts():
    questions = [q("26(i)", "Part i"), q("26(ii)", "Part ii"), q("26(iii)", "Part iii")]
    answers = [a("26(i)", "A1"), a("26(ii)", "A2"), a("26(iii)", "A3")]
    mappings = mapping_agent.run(questions, answers)
    assert mapping_for(mappings, "26(i)").match_level == "exact"
    assert mapping_for(mappings, "26(ii)").match_level == "exact"
    assert mapping_for(mappings, "26(iii)").match_level == "exact"


def test_multi_page_answer_regions_preserved_through_mapping():
    questions = [q("7", "Explain the process")]
    answers = [a("7", "Spans two pages", regions=[
        {"page": 3, "x": 0.1, "y": 0.1, "width": 0.5, "height": 0.2},
        {"page": 4, "x": 0.1, "y": 0.1, "width": 0.5, "height": 0.1},
    ])]
    mappings = mapping_agent.run(questions, answers)
    pages = sorted({r.page for r in mapping_for(mappings, "7").answer.regions})
    assert pages == [3, 4]


def test_no_exact_match_available_falls_through_priority_ladder_not_fuzzy_first():
    """An exact match must win even when a fuzzy-similar decoy exists."""
    questions = [q("1", "Q1"), q("11", "Q11 - a decoy that's fuzzy-similar to some noisy '1'-like input")]
    answers = [a("1", "Answer to exactly 1")]
    mappings = mapping_agent.run(questions, answers, enable_semantic=False)
    assert mapping_for(mappings, "1").match_level == "exact"
    assert mapping_for(mappings, "1").answer.text == "Answer to exactly 1"


def test_missing_question_number_uses_semantic_fallback_and_never_invents_a_number():
    """
    When the detected number doesn't match anything by string methods, the
    semantic fallback must only ever pick from the given candidate list (or
    return no match) - it must never be trusted to invent a number.
    """
    questions = [q("5", "What is photosynthesis?"), q("6", "What is respiration?")]
    answers = [a("???", "Plants convert sunlight into chemical energy using chlorophyll.")]

    with patch(
        "app.services.vision_service.run_structured_extraction",
        return_value={"matched_question_number": "5", "confidence": 0.8, "reasoning": "matches photosynthesis"},
    ):
        mappings = mapping_agent.run(questions, answers, enable_semantic=True)

    m = mapping_for(mappings, "5")
    assert m is not None
    assert m.match_level == "semantic"
    assert m.answer.text.startswith("Plants convert")


def test_semantic_fallback_returning_null_leaves_answer_unmatched():
    questions = [q("5", "What is photosynthesis?")]
    answers = [a("???", "Completely unrelated content about world history.")]

    with patch(
        "app.services.vision_service.run_structured_extraction",
        return_value={"matched_question_number": None, "confidence": 0.0, "reasoning": "no plausible match"},
    ):
        mappings = mapping_agent.run(questions, answers, enable_semantic=True)

    unmatched = [m for m in mappings if m.match_level == "unmatched"]
    assert len(unmatched) == 1


def test_low_confidence_never_silently_presented_as_confident():
    """
    A fuzzy match (score 0.8, well below a perfect 1.0) must be relabeled
    "low-confidence" rather than "fuzzy" once its score falls under the
    confidence bar - an exact/normalized match can never exercise this since
    their scores (1.0/0.9) are effectively always above any sane threshold,
    so this specifically constructs a fuzzy-tier pair.
    """
    question = Question(number="12(a)", normalized_number="12(a)", text="Explain photosynthesis.",
                         page=1, order=1)
    answer = Answer(detected_question_number="12(4)", normalized_question_number="12(4)",
                     text="An answer.", confidence=0.7,
                     regions=[AnswerRegion(page=1, x=0.1, y=0.1, width=0.5, height=0.1)])

    original_threshold = mapping_agent.LOW_CONFIDENCE_THRESHOLD
    try:
        # The fuzzy ratio for this pair is 0.8 - clears FUZZY_ACCEPT_SCORE
        # (0.72) so it's still accepted as a candidate, but raising the
        # confidence bar above 0.8 forces the relabel to "low-confidence".
        mapping_agent.LOW_CONFIDENCE_THRESHOLD = 0.85
        mappings = mapping_agent.run([question], [answer], enable_semantic=False)
        m = mapping_for(mappings, "12(a)")
        assert m is not None
        assert m.match_level == "low-confidence"
        assert m.match_score == pytest.approx(0.8)
    finally:
        mapping_agent.LOW_CONFIDENCE_THRESHOLD = original_threshold
