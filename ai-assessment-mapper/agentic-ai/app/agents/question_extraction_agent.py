"""Extracts every question from a question paper document."""
from pydantic import ValidationError

from app.prompts import question_prompt
from app.schemas.question_schema import Question, QuestionBoundingBox, QuestionExtractionResult
from app.services import vision_service
from app.services.pdf_service import PageImage, refine_text_region
from app.utils.normalization import normalize_question_number


def run(pages: list[PageImage], file_path: str | None = None) -> QuestionExtractionResult:
    raw = vision_service.run_structured_extraction(
        system_prompt=question_prompt.SYSTEM_PROMPT,
        user_prompt=question_prompt.build_user_prompt(len(pages)),
        pages=pages,
        tool_name=question_prompt.TOOL_NAME,
        tool_description=question_prompt.TOOL_DESCRIPTION,
        input_schema=question_prompt.INPUT_SCHEMA,
    )

    warnings: list[str] = list(raw.get("warnings", []))
    questions: list[Question] = []

    for order, item in enumerate(raw.get("questions", []), start=1):
        bbox = None
        raw_bbox = item.get("bounding_box")
        if file_path and item.get("text"):
            refined = refine_text_region(file_path, item.get("page", 0), item["text"])
            if refined:
                raw_bbox = refined
        if raw_bbox:
            try:
                bbox = QuestionBoundingBox(**raw_bbox)
            except ValidationError as exc:
                warnings.append(
                    f"Discarded invalid bounding box for question {item.get('number')}: {exc}"
                )

        try:
            question = Question(
                number=item["number"],
                normalized_number=normalize_question_number(item["number"]),
                text=item["text"],
                marks=item.get("marks"),
                page=item["page"],
                order=order,
                bounding_box=bbox,
            )
        except (ValidationError, KeyError) as exc:
            warnings.append(f"Skipped malformed question entry: {exc}")
            continue

        questions.append(question)

    return QuestionExtractionResult(
        questions=questions, page_count=len(pages), warnings=warnings
    )
