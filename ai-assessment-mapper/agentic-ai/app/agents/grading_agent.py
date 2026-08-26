"""Optional: grades mapped question/answer pairs and returns score + feedback.
Only runs on demand, after extraction and mapping are already complete."""
import json
import re

from app.prompts import grading_prompt
from app.schemas.assessment_schema import GradeResult, GradingResult, Mapping
from app.services import vision_service

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_grade_response(raw_text: str, question_number: str) -> GradeResult:
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

    return GradeResult(
        question_number=question_number,
        score=data.get("score"),
        max_score=data.get("max_score"),
        correct=data.get("correct"),
        feedback=data.get("feedback", ""),
    )


def run(mappings: list[Mapping]) -> GradingResult:
    grades: list[GradeResult] = []

    gradable = [m for m in mappings if m.question and m.answer]

    for mapping in gradable:
        try:
            raw_text = vision_service.run_text_completion(
                system_prompt=grading_prompt.SYSTEM_PROMPT,
                user_prompt=grading_prompt.build_user_prompt(
                    mapping.question.text, mapping.answer.text, mapping.question.marks
                ),
            )
            grades.append(_parse_grade_response(raw_text, mapping.question.number))
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
