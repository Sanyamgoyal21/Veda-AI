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
from app.services.pdf_service import load_document_pages


def process_assessment(question_file_path: str, answer_file_path: str) -> AssessmentResult:
    question_pages = load_document_pages(question_file_path)
    answer_pages = load_document_pages(answer_file_path)

    question_result = question_extraction_agent.run(question_pages)
    answer_result = answer_extraction_agent.run(answer_pages)

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


def grade_assessment(mappings_payload: list[dict]) -> dict:
    from app.schemas.assessment_schema import Mapping

    mappings = [Mapping(**m) for m in mappings_payload]
    result = grading_agent.run(mappings)
    return result.model_dump()
