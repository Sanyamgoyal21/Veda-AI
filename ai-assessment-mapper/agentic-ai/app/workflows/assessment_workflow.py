"""
Orchestrates the full agent pipeline. This is the only place that sequences
agents together - each agent stays independently testable and debuggable.

    Question Extraction   Answer Extraction
            |                     |
            +---------+-----------+
                      |
                Mapping Agent
                      |
               Validation Agent
                      |
              Assessment Result --(optional)--> Grading Agent
"""
from app.agents import (
    answer_extraction_agent,
    grading_agent,
    mapping_agent,
    question_extraction_agent,
    validation_agent,
)
from app.schemas.assessment_schema import AssessmentResult
from app.services.pdf_service import extract_full_text, load_document_pages


def process_assessment(question_file_path: str, answer_file_path: str) -> AssessmentResult:
    question_pages = load_document_pages(question_file_path)
    answer_pages = load_document_pages(answer_file_path)

    question_result = question_extraction_agent.run(question_pages, file_path=question_file_path)
    answer_result = answer_extraction_agent.run(
        answer_pages, file_path=answer_file_path, questions=question_result.questions
    )

    mappings = mapping_agent.run(question_result.questions, answer_result.answers)

    validation = validation_agent.run(
        question_result.questions,
        answer_result.answers,
        mappings,
        question_page_count=question_result.page_count,
        answer_page_count=answer_result.page_count,
    )

    return AssessmentResult(
        questions=question_result.questions,
        answers=answer_result.answers,
        mappings=mappings,
        validation=validation,
        grading=None,
    )


def grade_assessment(
    mappings_payload: list[dict],
    answer_file_path: str | None = None,
    marking_scheme_file_path: str | None = None,
) -> dict:
    from app.schemas.assessment_schema import Mapping

    mappings = [Mapping(**m) for m in mappings_payload]

    marking_scheme_text = None
    marking_scheme_pages = None
    if marking_scheme_file_path:
        marking_scheme_text = extract_full_text(marking_scheme_file_path)
        if not marking_scheme_text:
            # No text layer (a scanned marking scheme) - fall back to images.
            marking_scheme_pages = load_document_pages(marking_scheme_file_path)

    result = grading_agent.run(
        mappings,
        answer_file_path=answer_file_path,
        marking_scheme_text=marking_scheme_text,
        marking_scheme_pages=marking_scheme_pages,
    )
    return result.model_dump()
