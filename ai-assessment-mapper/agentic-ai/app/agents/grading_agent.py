"""
Rubric-based, criterion-level grading. Only runs on demand, after extraction
and mapping are already complete.

The model never states a final score - it awards marks per rubric criterion,
and this code (not the model) clamps each award to its criterion's max and
sums the total. This is deliberate: an LLM asked to both judge an answer AND
add up the marks will occasionally get the arithmetic wrong even when its
judgement is fine (observed during testing); separating "judge" from "sum"
removes that failure mode entirely, since Python addition doesn't make
mistakes.
"""
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.agents import rubric_agent
from app.prompts import grading_prompt
from app.schemas.assessment_schema import (
    CriterionGrade,
    GradeResult,
    GradingConfidence,
    GradingResult,
    Mapping,
    Rubric,
)
from app.services import vision_service
from app.services.image_service import crop_region
from app.services.pdf_service import PageImage, load_document_pages

DEFAULT_MAX_MARKS = 5
MAX_GRADING_WORKERS = max(1, int(os.getenv("GRADING_MAX_WORKERS", "4")))


def _confidence_bucket(
    rubric: Rubric, has_image: bool, mismatch: bool, was_clamped: bool, answer_confidence: float
) -> GradingConfidence:
    """
    Computed from evidence, not copied from the model's own self-reported
    confidence: a teacher-grounded rubric with the real answer image visible
    and no correction needed is "high"; an AI-guessed rubric with no image
    and a shaky transcription is "low"; everything else is "medium". A
    detected mismatch is itself a confident (if unwelcome) determination.
    """
    if mismatch:
        return "high"
    if rubric.source == "teacher" and has_image and not was_clamped and answer_confidence >= 0.6:
        return "high"
    if rubric.source == "ai" and (not has_image or answer_confidence < 0.5):
        return "low"
    return "medium"


def _load_answer_page_images(answer_file_path: str | None) -> dict:
    if not answer_file_path:
        return {}
    try:
        pages = load_document_pages(answer_file_path)
    except Exception:
        return {}
    return {p.page: p.image for p in pages}


def _crop_answer_images(mapping: Mapping, page_images: dict) -> list[PageImage]:
    crops: list[PageImage] = []
    for region in mapping.answer.regions:
        page_image = page_images.get(region.page)
        if page_image is None:
            continue
        cropped = crop_region(page_image, region.x, region.y, region.width, region.height)
        crops.append(PageImage(page=region.page, image=cropped))
    return crops


def _grade_one(mapping: Mapping, rubric: Rubric, answer_crops: list[PageImage]) -> GradeResult:
    rubric_payload = [{"criterion": c.criterion, "max_marks": c.max_marks} for c in rubric.criteria]

    try:
        raw = vision_service.run_structured_extraction(
            system_prompt=grading_prompt.SYSTEM_PROMPT,
            user_prompt=grading_prompt.build_user_prompt(
                mapping.question.text,
                rubric_payload,
                rubric.reference_answer,
                mapping.answer.text,
                bool(answer_crops),
            ),
            pages=answer_crops,
            tool_name=grading_prompt.TOOL_NAME,
            tool_description=grading_prompt.TOOL_DESCRIPTION,
            input_schema=grading_prompt.INPUT_SCHEMA,
        )
    except vision_service.VisionServiceError as exc:
        return GradeResult(
            question_number=mapping.question.number,
            feedback=f"Grading unavailable: {exc}",
            rubric_source=rubric.source,
            confidence="low",
        )

    mismatch = bool(raw.get("mismatch_suspected"))
    model_criteria = raw.get("criteria", [])

    if len(model_criteria) == len(rubric.criteria):
        pairs = list(zip(rubric.criteria, model_criteria))
    else:
        # Model didn't return one entry per rubric criterion - match by name
        # so a partial/malformed response never silently drops a criterion.
        pairs = []
        for rc in rubric.criteria:
            match = next((mc for mc in model_criteria if mc.get("criterion") == rc.criterion), None)
            pairs.append((rc, match or {"awarded_marks": 0, "evidence": "(no matching criterion returned)"}))

    graded_criteria: list[CriterionGrade] = []
    was_clamped = False

    for rubric_criterion, model_criterion in pairs:
        raw_awarded = 0 if mismatch else (model_criterion.get("awarded_marks") or 0)
        try:
            raw_awarded = float(raw_awarded)
        except (TypeError, ValueError):
            raw_awarded = 0.0
        awarded = max(0.0, min(raw_awarded, rubric_criterion.max_marks))
        if awarded != raw_awarded:
            was_clamped = True
        graded_criteria.append(
            CriterionGrade(
                criterion=rubric_criterion.criterion,
                max_marks=rubric_criterion.max_marks,
                awarded_marks=awarded,
                evidence=model_criterion.get("evidence", ""),
            )
        )

    total = sum(c.awarded_marks for c in graded_criteria)
    max_total = sum(c.max_marks for c in graded_criteria)
    total = min(total, max_total)  # never exceed the maximum, defensively

    confidence = _confidence_bucket(rubric, bool(answer_crops), mismatch, was_clamped, mapping.answer.confidence)

    return GradeResult(
        question_number=mapping.question.number,
        score=total,
        max_score=max_total,
        criteria=graded_criteria,
        rubric_source=rubric.source,
        confidence=confidence,
        correct=False if mismatch else (total >= max_total * 0.5 if max_total else None),
        feedback=raw.get("feedback", ""),
        mismatch_suspected=mismatch,
    )


def _validate_grades(grades: list[GradeResult]) -> list[str]:
    """
    Defense-in-depth sanity pass. Every one of these should be structurally
    impossible given the clamping in `_grade_one`, but a validation step
    that trusts its own invariants without checking them isn't validation -
    if a future change ever breaks one of these, this is what catches it
    instead of silently shipping a wrong mark to a student.
    """
    issues: list[str] = []
    for g in grades:
        if g.score is not None and g.max_score is not None and g.score > g.max_score + 0.01:
            issues.append(f"Question '{g.question_number}': score {g.score} exceeds max {g.max_score}")
        if g.score is not None and g.score < -0.01:
            issues.append(f"Question '{g.question_number}': negative score {g.score}")

        criteria_total = sum(c.awarded_marks for c in g.criteria)
        if g.score is not None and abs(criteria_total - g.score) > 0.01:
            issues.append(
                f"Question '{g.question_number}': score {g.score} does not match "
                f"sum of criteria {criteria_total}"
            )
        for c in g.criteria:
            if c.awarded_marks > c.max_marks + 0.01 or c.awarded_marks < -0.01:
                issues.append(
                    f"Question '{g.question_number}' criterion '{c.criterion}': "
                    f"awarded {c.awarded_marks} out of range [0, {c.max_marks}]"
                )
    return issues


def run(
    mappings: list[Mapping],
    answer_file_path: str | None = None,
    marking_scheme_text: str | None = None,
    marking_scheme_pages: list[PageImage] | None = None,
) -> GradingResult:
    grades: list[GradeResult] = []
    warnings: list[str] = []

    gradable = [m for m in mappings if m.question and m.answer]
    unanswered = [m for m in mappings if m.question and not m.answer]

    # A question with no matching answer was not attempted - that's a
    # deterministic 0, not a question left out of the total. No AI call
    # needed: there is no answer to evaluate.
    for mapping in unanswered:
        marks = mapping.question.marks or DEFAULT_MAX_MARKS
        grades.append(
            GradeResult(
                question_number=mapping.question.number,
                score=0,
                max_score=marks,
                criteria=[
                    CriterionGrade(
                        criterion="Attempted",
                        max_marks=marks,
                        awarded_marks=0,
                        evidence="No matching answer was found on the answer sheet.",
                    )
                ],
                rubric_source="ai",
                confidence="high",  # certain: there is nothing to grade
                correct=False,
                feedback="Not attempted - no matching answer was found on the answer sheet.",
            )
        )

    page_images = _load_answer_page_images(answer_file_path)

    def grade_mapping(mapping: Mapping) -> GradeResult:
        rubric = rubric_agent.generate(mapping.question, marking_scheme_text, marking_scheme_pages)
        answer_crops = _crop_answer_images(mapping, page_images)
        return _grade_one(mapping, rubric, answer_crops)

    # Each question is independent. A small bounded pool avoids the previous
    # 2*N sequential provider round trips without flooding the provider.
    completed: dict[int, GradeResult] = {}
    with ThreadPoolExecutor(max_workers=min(MAX_GRADING_WORKERS, len(gradable) or 1)) as executor:
        futures = {executor.submit(grade_mapping, mapping): (index, mapping) for index, mapping in enumerate(gradable)}
        for future in as_completed(futures):
            index, mapping = futures[future]
            try:
                completed[index] = future.result()
            except vision_service.VisionServiceError as exc:
                warnings.append(f"Could not build a rubric for question '{mapping.question.number}': {exc}")

    for index in sorted(completed):
        grades.append(completed[index])

    warnings.extend(_validate_grades(grades))

    total_score = sum(g.score for g in grades if g.score is not None) if grades else None
    total_max = sum(g.max_score for g in grades if g.max_score is not None) if grades else None
    percentage = round(total_score / total_max * 100, 1) if total_score is not None and total_max else None

    return GradingResult(
        grades=grades,
        total_score=total_score,
        total_max_score=total_max,
        percentage=percentage,
        warnings=warnings,
    )
