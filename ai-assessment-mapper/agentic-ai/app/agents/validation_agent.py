"""Validates the full extraction + mapping result before it reaches the
frontend. Never lets a silently-wrong result through - everything suspicious
becomes an explicit warning or error."""
from collections import Counter

from app.schemas.answer_schema import Answer
from app.schemas.assessment_schema import Mapping, ValidationResult
from app.schemas.question_schema import Question


def run(
    questions: list[Question],
    answers: list[Answer],
    mappings: list[Mapping],
    question_page_count: int,
    answer_page_count: int,
) -> ValidationResult:
    warnings: list[str] = []
    errors: list[str] = []

    # Duplicate questions (same normalized number extracted twice).
    number_counts = Counter(q.normalized_number for q in questions if q.normalized_number)
    for number, count in number_counts.items():
        if count > 1:
            warnings.append(f"Question '{number}' was extracted {count} times (possible duplicate)")

    # Invalid / empty question numbers.
    for q in questions:
        if not q.normalized_number:
            errors.append(f"Question with text '{q.text[:40]}...' has an unparseable number")
        if q.page < 1 or q.page > question_page_count:
            errors.append(f"Question '{q.number}' references invalid page {q.page}")

    # Missing questions: gaps in the main numeric sequence.
    main_numbers = sorted(
        {int(n) for n in (q.normalized_number.split("(")[0] for q in questions) if n.isdigit()}
    )
    for a, b in zip(main_numbers, main_numbers[1:]):
        if b - a > 1:
            missing = ", ".join(str(n) for n in range(a + 1, b))
            warnings.append(f"Possible missing question number(s): {missing}")

    # Bounding box sanity (schema already enforces 0-1 ranges; check degenerate sizes).
    for answer in answers:
        for region in answer.regions:
            if region.page < 1 or region.page > answer_page_count:
                errors.append(
                    f"Answer '{answer.detected_question_number}' references invalid page {region.page}"
                )
            if region.width <= 0 or region.height <= 0:
                errors.append(
                    f"Answer '{answer.detected_question_number}' has a zero-area bounding box"
                )

    # Mapping-derived stats.
    answered = [m for m in mappings if m.match_level not in ("unanswered", "unmatched")]
    unanswered = [m for m in mappings if m.match_level == "unanswered"]
    unmatched = [m for m in mappings if m.match_level == "unmatched"]
    low_confidence = [m for m in mappings if m.match_level == "low-confidence"]

    for m in low_confidence:
        warnings.append(
            f"Mapping for question '{m.question_number}' has low confidence "
            f"({m.match_score:.2f})"
        )

    for m in unmatched:
        warnings.append(
            f"Answer detected as '{m.answer_question_number}' has no matching question"
        )

    # Duplicate answer-to-question mappings (defensive; mapping_agent should prevent this).
    mapped_question_numbers = [m.question_number for m in answered if m.question_number]
    for number, count in Counter(mapped_question_numbers).items():
        if count > 1:
            errors.append(f"Question '{number}' received {count} mapped answers")

    stats = {
        "total_questions": len(questions),
        "total_answers": len(answers),
        "answered": len(answered),
        "unanswered": len(unanswered),
        "unmatched": len(unmatched),
        "low_confidence": len(low_confidence),
    }

    return ValidationResult(valid=len(errors) == 0, warnings=warnings, errors=errors, stats=stats)
