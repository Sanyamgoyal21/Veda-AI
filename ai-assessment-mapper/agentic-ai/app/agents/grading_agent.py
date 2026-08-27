"""Optional: grades mapped question/answer pairs and returns score + feedback.
Only runs on demand, after extraction and mapping are already complete."""
import json
import re

from app.prompts import grading_prompt
from app.schemas.assessment_schema import GradeResult, GradingResult, Mapping
from app.services import vision_service

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)

# Mirrors grading_prompt's own fallback when a question has no printed marks.
DEFAULT_MAX_SCORE = 5


def _parse_grade_response(raw_text: str, question_number: str, fallback_max_score: float) -> GradeResult:
    match = _JSON_RE.search(raw_text)
    if not match:
        return GradeResult(
            question_number=question_number,
            feedback="AI grading response could not be parsed.",
        )
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return GradeResult(
            question_number=question_number,
            feedback="AI grading response could not be parsed.",
        )

    mismatch = bool(data.get("mismatch_suspected"))
    max_score = data.get("max_score") or fallback_max_score

    return GradeResult(
        question_number=question_number,
        # Don't trust the model's own score for a flagged mismatch - a
        # different-topic answer is worth 0 regardless of what it reasoned.
        score=0 if mismatch else data.get("score"),
        max_score=max_score,
        correct=False if mismatch else data.get("correct"),
        feedback=data.get("feedback", ""),
        mismatch_suspected=mismatch,
    )


def run(mappings: list[Mapping]) -> GradingResult:
    grades: list[GradeResult] = []

    gradable = [m for m in mappings if m.question and m.answer]
    unanswered = [m for m in mappings if m.question and not m.answer]

    # A question with no matching answer was not attempted - that's a 0, not
    # a question left out of the total. No AI call needed: there is no
    # answer text to evaluate, so the score is deterministic.
    for mapping in unanswered:
        grades.append(
            GradeResult(
                question_number=mapping.question.number,
                score=0,
                max_score=mapping.question.marks or DEFAULT_MAX_SCORE,
                correct=False,
                feedback="Not attempted - no matching answer was found on the answer sheet.",
            )
        )

    for mapping in gradable:
        try:
            raw_text = vision_service.run_text_completion(
                system_prompt=grading_prompt.SYSTEM_PROMPT,
                user_prompt=grading_prompt.build_user_prompt(
                    mapping.question.text, mapping.answer.text, mapping.question.marks
                ),
            )
            fallback_max_score = mapping.question.marks or DEFAULT_MAX_SCORE
            grades.append(_parse_grade_response(raw_text, mapping.question.number, fallback_max_score))
        except vision_service.VisionServiceError as exc:
            grades.append(
                GradeResult(
                    question_number=mapping.question.number,
                    feedback=f"Grading unavailable: {exc}",
                )
            )

    scored = [g for g in grades if g.score is not None and g.max_score]
    total_score = sum(g.score for g in scored) if scored else None
    total_max = sum(g.max_score for g in scored) if scored else None
    percentage = (total_score / total_max * 100) if total_score is not None and total_max else None

    return GradingResult(
        grades=grades,
        total_score=total_score,
        total_max_score=total_max,
        percentage=round(percentage, 1) if percentage is not None else None,
    )
