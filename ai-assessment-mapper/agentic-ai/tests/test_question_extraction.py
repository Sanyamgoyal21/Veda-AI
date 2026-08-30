"""
Regression tests for the deterministic MCQ-option-vs-sub-part merge logic.
No AI calls - operates directly on the raw item dicts a model response
would produce, exactly as question_extraction_agent.run() consumes them.
"""
from app.agents.question_extraction_agent import _looks_like_mcq_options, _merge_mcq_option_siblings


def _item(number, text, page=1, marks=None):
    d = {"number": number, "text": text, "page": page}
    if marks is not None:
        d["marks"] = marks
    return d


def test_mcq_options_are_detected_and_merged_into_one_question():
    items = [
        _item("1(a)", "The HCF of 96 and 404 is 4"),
        _item("1(b)", "The HCF of 96 and 404 is 8"),
        _item("1(c)", "The HCF of 96 and 404 is 12"),
        _item("1(d)", "The HCF of 96 and 404 is 16"),
    ]
    merged, warnings = _merge_mcq_option_siblings(items)

    assert len(merged) == 1
    assert merged[0]["number"] == "1"
    assert "(a) 4" in merged[0]["text"]
    assert "(b) 8" in merged[0]["text"]
    assert "(c) 12" in merged[0]["text"]
    assert "(d) 16" in merged[0]["text"]
    assert len(warnings) == 1


def test_genuine_lettered_subparts_are_never_merged():
    # Each part asks for something substantively different - not a short
    # value picked from a shared stem - so these must stay as two questions.
    items = [
        _item("5(a)", "Name an acid."),
        _item("5(b)", "Name a base."),
    ]
    merged, warnings = _merge_mcq_option_siblings(items)

    assert len(merged) == 2
    assert {q["number"] for q in merged} == {"5(a)", "5(b)"}
    assert warnings == []


def test_roman_numeral_subparts_are_never_touched():
    # "21(ii)" doesn't match the single-letter parent pattern at all, and a
    # lone "21(i)" never reaches the length>=2 merge check.
    items = [
        _item("21(i)", "Two dice are thrown together. Find the probability that the sum is 7."),
        _item("21(ii)", "Two dice are thrown together. Find the probability that the sum is a prime number."),
    ]
    merged, warnings = _merge_mcq_option_siblings(items)

    assert len(merged) == 2
    assert {q["number"] for q in merged} == {"21(i)", "21(ii)"}
    assert warnings == []


def test_unrelated_questions_pass_through_untouched():
    items = [_item("1", "Define velocity."), _item("2", "Define acceleration.")]
    merged, warnings = _merge_mcq_option_siblings(items)
    assert merged == items
    assert warnings == []


def test_looks_like_mcq_options_rejects_dissimilar_texts():
    assert not _looks_like_mcq_options(["Name an acid.", "Name a base."])
    assert not _looks_like_mcq_options(["Find the probability the sum is 7.", "Find the probability the sum is a prime number."])


def test_looks_like_mcq_options_accepts_short_shared_stem_values():
    assert _looks_like_mcq_options([
        "The HCF of 96 and 404 is 4",
        "The HCF of 96 and 404 is 8",
        "The HCF of 96 and 404 is 12",
        "The HCF of 96 and 404 is 16",
    ])


def test_mcq_options_with_phrase_values_are_also_merged():
    # Real reported case: options are short PHRASES, not bare numbers - the
    # original heuristic's word-count cap rejected these outright.
    items = [
        _item("3(a)", "The pair of linear equations x + 2y = 5 and 2x + 4y = 10 has No solution"),
        _item("3(b)", "The pair of linear equations x + 2y = 5 and 2x + 4y = 10 has Unique solution"),
        _item("3(c)", "The pair of linear equations x + 2y = 5 and 2x + 4y = 10 has Infinitely many solutions"),
        _item("3(d)", "The pair of linear equations x + 2y = 5 and 2x + 4y = 10 has Exactly two solutions"),
    ]
    merged, warnings = _merge_mcq_option_siblings(items)

    assert len(merged) == 1
    assert merged[0]["number"] == "3"
    assert "(a) No solution" in merged[0]["text"]
    assert "(c) Infinitely many solutions" in merged[0]["text"]
    assert len(warnings) == 1


def test_mcq_options_describing_root_types_are_merged():
    items = [
        _item("4(a)", "If the discriminant of a quadratic equation is negative, the roots are Real and equal"),
        _item("4(b)", "If the discriminant of a quadratic equation is negative, the roots are Real and distinct"),
        _item("4(c)", "If the discriminant of a quadratic equation is negative, the roots are Not real"),
        _item("4(d)", "If the discriminant of a quadratic equation is negative, the roots are Complex conjugate"),
    ]
    merged, warnings = _merge_mcq_option_siblings(items)

    assert len(merged) == 1
    assert merged[0]["number"] == "4"
    assert len(warnings) == 1


def test_mcq_merge_does_not_trigger_on_non_sequential_letters():
    # A stray "1(a)" and "1(c)" (no "1(b)") is not the standard MCQ shape -
    # too suspicious to merge confidently, so leave both alone.
    items = [
        _item("1(a)", "The HCF of 96 and 404 is 4"),
        _item("1(c)", "The HCF of 96 and 404 is 12"),
    ]
    merged, warnings = _merge_mcq_option_siblings(items)
    assert len(merged) == 2
    assert warnings == []
