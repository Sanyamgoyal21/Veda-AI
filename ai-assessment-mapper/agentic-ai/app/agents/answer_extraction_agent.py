"""Extracts every handwritten answer (with exact page regions) from a
student's answer sheet document."""
from pydantic import ValidationError

from app.prompts import answer_prompt
from app.schemas.answer_schema import Answer, AnswerExtractionResult, AnswerRegion
from app.services import vision_service
from app.services.pdf_service import PageImage
from app.utils.normalization import normalize_question_number


def run(pages: list[PageImage]) -> AnswerExtractionResult:
    raw = vision_service.run_structured_extraction(
        system_prompt=answer_prompt.SYSTEM_PROMPT,
        user_prompt=answer_prompt.build_user_prompt(len(pages)),
        pages=pages,
        tool_name=answer_prompt.TOOL_NAME,
        tool_description=answer_prompt.TOOL_DESCRIPTION,
        input_schema=answer_prompt.INPUT_SCHEMA,
    )

    warnings: list[str] = list(raw.get("warnings", []))
    answers: list[Answer] = []

    for item in raw.get("answers", []):
        regions: list[AnswerRegion] = []
        for raw_region in item.get("regions", []):
            try:
                regions.append(AnswerRegion(**raw_region))
            except ValidationError as exc:
                warnings.append(
                    f"Discarded invalid region for answer "
                    f"{item.get('detected_question_number')}: {exc}"
                )

        if not regions:
            warnings.append(
                f"Answer {item.get('detected_question_number')} had no valid "
                "regions and was dropped"
            )
            continue

        try:
            answer = Answer(
                detected_question_number=item["detected_question_number"],
                normalized_question_number=normalize_question_number(
                    item["detected_question_number"]
                ),
                text=item["text"],
                confidence=item.get("confidence", 0.5),
                regions=regions,
            )
        except (ValidationError, KeyError) as exc:
            warnings.append(f"Skipped malformed answer entry: {exc}")
            continue

        answers.append(answer)

    return AnswerExtractionResult(answers=answers, page_count=len(pages), warnings=warnings)
