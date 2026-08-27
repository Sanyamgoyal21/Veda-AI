"""
Deterministic tests for question-number normalization and ordering. No AI
calls, no mocking - these are pure functions and should behave identically
on every run.
"""
import random

from app.utils.normalization import extract_order_key, normalize_question_number


def test_normalizes_letter_subpart_variants():
    variants = ["11(a)", "11 (a)", "Q11(a)", "11-A", "11 - a", "11a"]
    normalized = {normalize_question_number(v) for v in variants}
    assert normalized == {"11(a)"}


def test_normalizes_roman_numeral_subpart_variants():
    variants = ["26(ii)", "26 (ii)", "Q26-ii", "26-ii"]
    normalized = {normalize_question_number(v) for v in variants}
    assert normalized == {"26(ii)"}


def test_normalizes_double_nested_subparts():
    variants = ["11(a)(i)", "11 (a) (i)", "Q.11(a)(i)", "11-a-i"]
    normalized = {normalize_question_number(v) for v in variants}
    assert normalized == {"11(a)(i)"}


def test_bare_numbers_untouched():
    assert normalize_question_number("1") == "1"
    assert normalize_question_number("  3  ") == "3"
    assert normalize_question_number("Q.2") == "2"


def test_continuation_label_normalizes_same_as_bare_number():
    """
    Regression test: a model that writes "Q5 continued" instead of repeating
    "Q5" on a continuation page must still normalize to the same key as
    "Q5", or multi-page answer merging silently breaks.
    """
    assert normalize_question_number("Q5 continued") == normalize_question_number("Q5") == "5"


def test_extract_order_key_orders_parents_before_subparts():
    numbers = ["2", "2(a)", "10", "10(a)", "10(a)(i)", "10(a)(ii)", "10(b)", "10(i)", "11"]
    shuffled = numbers[:]
    random.shuffle(shuffled)
    assert sorted(shuffled, key=extract_order_key) == numbers


def test_extract_order_key_unparseable_numbers_sort_last_but_deterministically():
    ordered = sorted(["garbage-1", "garbage-2", "1"], key=extract_order_key)
    assert ordered[0] == "1"
    assert ordered[1:] == sorted(["garbage-1", "garbage-2"])  # deterministic among themselves
