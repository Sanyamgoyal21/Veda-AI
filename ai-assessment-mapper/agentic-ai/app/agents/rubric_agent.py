"""
Generates a marking rubric for one question, before any student answer is
considered. Two modes:

  Mode A (teacher-provided): a marking scheme document was uploaded and
  actually covers this question - criteria and reference answer are grounded
  in it, source="teacher" (higher grading confidence downstream).

  Mode B (no marking scheme, or it doesn't cover this question): the rubric
  is generated from the question text alone, source="ai" (lower confidence).

Which mode applies is decided per-question from the model's own factual
report of whether it found relevant material - never assumed just because a
file was uploaded, since a marking scheme rarely covers every question.
"""
from app.prompts import rubric_prompt
from app.schemas.assessment_schema import Rubric, RubricCriterion
from app.schemas.question_schema import Question
from app.services import vision_service
from app.services.pdf_service import PageImage

DEFAULT_MAX_MARKS = 5


def _normalize_to_target(criteria: list[RubricCriterion], target: float) -> list[RubricCriterion]:
    """
    Deterministically rescales criteria so their marks sum to exactly
    `target` - the model is asked to keep them "roughly proportionate", not
    to get the arithmetic exactly right, because that's not its job.
    """
    total = sum(c.max_marks for c in criteria)
    if total <= 0:
        return [RubricCriterion(criterion=c.criterion, max_marks=0) for c in criteria] or [
            RubricCriterion(criterion="Overall correctness", max_marks=target)
        ]
    if abs(total - target) < 0.01:
        return criteria

    scale = target / total
    rescaled = [RubricCriterion(criterion=c.criterion, max_marks=round(c.max_marks * scale, 2)) for c in criteria]

    residual = round(target - sum(c.max_marks for c in rescaled), 2)
    if residual:
        rescaled[-1] = RubricCriterion(
            criterion=rescaled[-1].criterion,
            max_marks=max(0.0, round(rescaled[-1].max_marks + residual, 2)),
        )
    return rescaled


def generate(
    question: Question,
    marking_scheme_text: str | None = None,
    marking_scheme_pages: list[PageImage] | None = None,
) -> Rubric:
    marks_target = question.marks or DEFAULT_MAX_MARKS
    has_reference = bool(marking_scheme_text) or bool(marking_scheme_pages)

    raw = vision_service.run_structured_extraction(
        system_prompt=rubric_prompt.SYSTEM_PROMPT,
        user_prompt=rubric_prompt.build_user_prompt(
            question.text,
            question.marks,
            reference_text=marking_scheme_text,
            has_reference_images=bool(marking_scheme_pages),
        ),
        # Only spend image tokens when there's no cheaper text alternative.
        pages=(marking_scheme_pages or []) if not marking_scheme_text else [],
        tool_name=rubric_prompt.TOOL_NAME,
        tool_description=rubric_prompt.TOOL_DESCRIPTION,
        input_schema=rubric_prompt.INPUT_SCHEMA,
        max_tokens=1024,
    )

    criteria = [
        RubricCriterion(criterion=c["criterion"], max_marks=max(0.0, c.get("max_marks", 0)))
        for c in raw.get("criteria", [])
        if c.get("criterion")
    ]
    if not criteria:
        criteria = [RubricCriterion(criterion="Overall correctness", max_marks=marks_target)]

    criteria = _normalize_to_target(criteria, marks_target)
    used_reference = bool(raw.get("used_reference_material")) and has_reference

    return Rubric(
        question_number=question.number,
        criteria=criteria,
        reference_answer=raw.get("reference_answer"),
        source="teacher" if used_reference else "ai",
    )
