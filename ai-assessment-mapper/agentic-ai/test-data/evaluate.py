"""
Runs the real mapping_agent + validation_agent against small synthetic
"already extracted" question/answer sets and checks the result against a
hand-written expected mapping.

No live API key is needed for the vast majority of cases (they resolve
through the deterministic exact/normalized/fuzzy tiers); a small number of
cases that specifically test the semantic fallback (missing/ambiguous
question numbers) supply a `mockSemantic` response in their fixture so the
whole suite stays free, fast, and fully repeatable in CI.

This does NOT test the extraction agents themselves (that needs a real
vision model and was verified manually against the live API during
development - see README's "Known limitations"). It tests the mapping and
validation logic that runs on whatever extraction produces, which is exactly
the part that can be tested deterministically and cheaply - and it is
precisely this layer where the bugs fixed during development were found and
are now guarded against (see the case_regression_* fixtures).

Usage:
    cd agentic-ai
    venv/Scripts/python.exe test-data/evaluate.py
"""
import json
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.agents import mapping_agent, validation_agent
from app.schemas.answer_schema import Answer, AnswerRegion
from app.schemas.question_schema import Question
from app.utils.normalization import extract_order_key, normalize_question_number

CASES_DIR = os.path.dirname(__file__)


def load_case(case_dir: str):
    with open(os.path.join(case_dir, "questions.json")) as f:
        raw_questions = json.load(f)["questions"]
    with open(os.path.join(case_dir, "answers.json")) as f:
        raw_answers = json.load(f)["answers"]
    with open(os.path.join(case_dir, "expected_mappings.json")) as f:
        expected = json.load(f)

    questions = [
        Question(
            number=q["number"],
            normalized_number=normalize_question_number(q["number"]),
            text=q["text"],
            marks=q.get("marks"),
            page=q["page"],
            order=0,
        )
        for q in raw_questions
    ]
    questions.sort(key=lambda q: (extract_order_key(q.normalized_number), q.page))
    for order, question in enumerate(questions, start=1):
        question.order = order

    answers = [
        Answer(
            detected_question_number=a["detected_question_number"] or "",
            normalized_question_number=normalize_question_number(a["detected_question_number"] or ""),
            text=a["text"],
            confidence=a.get("confidence", 0.9),
            regions=[AnswerRegion(**r) for r in a["regions"]],
        )
        for a in raw_answers
    ]
    return questions, answers, expected


def evaluate_case(name: str, case_dir: str) -> dict:
    questions, answers, expected = load_case(case_dir)
    expected_mappings = expected["expectedMappings"]
    mock_semantic = expected.get("mockSemantic")

    if mock_semantic:
        with patch("app.services.vision_service.run_structured_extraction", return_value=mock_semantic):
            mappings = mapping_agent.run(questions, answers, enable_semantic=True)
    else:
        mappings = mapping_agent.run(questions, answers, enable_semantic=False)

    validation = validation_agent.run(
        questions, answers, mappings, question_page_count=99, answer_page_count=99
    )

    per_question = []  # (question_number, correct: bool, category: str)

    for number, expectation in expected_mappings.items():
        mapping = next((m for m in mappings if m.question_number == number), None)
        is_subquestion = "(" in number

        if expectation is None:
            correct = mapping is not None and mapping.match_level == "unanswered"
            per_question.append((number, correct, "unanswered", is_subquestion, False))
        else:
            answered = mapping is not None and mapping.match_level not in ("unanswered", "unmatched")
            correct = answered and mapping.answer.detected_question_number == expectation
            is_multipage = number in expected.get("multiPageQuestions", [])
            per_question.append((number, correct, "answered", is_subquestion, is_multipage))

    # Unmatched-answer detection: does the exact set of answers we expect to
    # end up unmatched match what actually happened?
    actual_unmatched_ids = {m.answer_question_number for m in mappings if m.match_level == "unmatched"}
    if "expectedUnmatchedAnswerIds" in expected:
        expected_unmatched_ids = set(expected["expectedUnmatchedAnswerIds"])
        unmatched_correct = actual_unmatched_ids == expected_unmatched_ids
    else:
        unmatched_correct = len(actual_unmatched_ids) == expected.get("expectedUnmatchedCount", 0)

    return {
        "name": name,
        "per_question": per_question,
        "unmatched_correct": unmatched_correct,
        "unmatched_expected": expected.get("expectedUnmatchedCount", len(expected.get("expectedUnmatchedAnswerIds", []))),
        "unmatched_actual": len(actual_unmatched_ids),
        "validation_valid": validation.valid,
    }


def aggregate(results: list[dict]) -> dict:
    all_q = [pq for r in results for pq in r["per_question"]]

    def acc(items):
        return (sum(1 for _, ok, *_ in items if ok) / len(items) * 100) if items else None

    unanswered_items = [pq for pq in all_q if pq[2] == "unanswered"]
    answered_items = [pq for pq in all_q if pq[2] == "answered"]
    subquestion_items = [pq for pq in all_q if pq[3]]
    multipage_items = [pq for pq in all_q if pq[4]]

    correct = sum(1 for _, ok, *_ in all_q if ok)
    incorrect = len(all_q) - correct

    return {
        "total": len(all_q),
        "correct": correct,
        "incorrect": incorrect,
        "mapping_accuracy": acc(all_q),
        "sub_question_accuracy": acc(subquestion_items),
        "unanswered_accuracy": acc(unanswered_items),
        "multi_page_accuracy": acc(multipage_items),
        "unmatched_detection": (sum(1 for r in results if r["unmatched_correct"]) / len(results) * 100) if results else None,
        "answered_accuracy": acc(answered_items),
    }


def main():
    case_dirs = sorted(
        d for d in os.listdir(CASES_DIR)
        if os.path.isdir(os.path.join(CASES_DIR, d)) and d.startswith("case_")
    )

    results = [evaluate_case(name, os.path.join(CASES_DIR, name)) for name in case_dirs]
    agg = aggregate(results)

    print("=" * 40)
    print("ANSWER MAPPING EVALUATION")
    print("=" * 40)
    print(f"\nCases run: {len(results)}")
    print(f"Questions evaluated: {agg['total']}\n")
    print(f"Correct mappings:   {agg['correct']:4d}")
    print(f"Incorrect mappings: {agg['incorrect']:4d}\n")
    print(f"Mapping accuracy:      {agg['mapping_accuracy']:.2f}%\n")
    print(f"Sub-question accuracy: {_fmt(agg['sub_question_accuracy'])}")
    print(f"Unmatched detection:   {_fmt(agg['unmatched_detection'])}")
    print(f"Unanswered detection:  {_fmt(agg['unanswered_accuracy'])}")
    print(f"Multi-page mapping:    {_fmt(agg['multi_page_accuracy'])}")
    print("=" * 40)

    print("\nPer-case detail:")
    print(f"{'case':45} {'correct/total':>14} {'unmatched':>10} {'valid':>7}")
    failing_cases = []
    for r in results:
        n_correct = sum(1 for _, ok, *_ in r["per_question"] if ok)
        n_total = len(r["per_question"])
        unmatched_status = "OK" if r["unmatched_correct"] else "MISMATCH"
        if n_correct != n_total or not r["unmatched_correct"]:
            failing_cases.append(r["name"])
        print(f"{r['name']:45} {n_correct:>6}/{n_total:<7} {unmatched_status:>10} {str(r['validation_valid']):>7}")

    if failing_cases:
        print("\nFAILING CASES:", ", ".join(failing_cases))
        sys.exit(1)


def _fmt(value):
    return f"{value:.1f}%" if value is not None else "n/a (no cases of this type)"


if __name__ == "__main__":
    main()
