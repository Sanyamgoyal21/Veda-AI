"""
Maps extracted answers to extracted questions using a strict priority ladder:

  Level 1  exact question number match
  Level 2  normalized question number match (handles "Q11(a)", "11 (a)", "11-A")
  Level 3  fuzzy string match on normalized numbers (OCR/handwriting noise)
  Level 4  semantic/content match via the vision/text model (last resort)
  Level 5  if nothing clears the confidence bar, the mapping is still returned
           but explicitly labelled "low-confidence" - it is never silently
           presented as a confident match.

Every question and every answer ends up in the output: unanswered questions
and unmatched answers are represented explicitly rather than dropped.
"""
from dataclasses import dataclass

from rapidfuzz import fuzz

from app.prompts import mapping_prompt
from app.schemas.answer_schema import Answer
from app.schemas.assessment_schema import Mapping
from app.schemas.question_schema import Question
from app.services import vision_service
from app.utils.confidence import (
    EXACT_SCORE,
    FUZZY_MIN_SCORE,
    LOW_CONFIDENCE_THRESHOLD,
    NORMALIZED_SCORE,
    SEMANTIC_MIN_SCORE,
)

FUZZY_ACCEPT_SCORE = 0.72  # rapidfuzz ratio (0-1) required to accept as "fuzzy"


@dataclass
class _Candidate:
    question: Question
    level: str
    score: float


def _try_exact_and_normalized(question: Question, answer: Answer) -> _Candidate | None:
    if question.number.strip() == answer.detected_question_number.strip():
        return _Candidate(question, "exact", EXACT_SCORE)
    if question.normalized_number and question.normalized_number == answer.normalized_question_number:
        return _Candidate(question, "normalized", NORMALIZED_SCORE)
    return None


def _try_fuzzy(question: Question, answer: Answer) -> _Candidate | None:
    if not question.normalized_number or not answer.normalized_question_number:
        return None
    ratio = fuzz.ratio(question.normalized_number, answer.normalized_question_number) / 100.0
    if ratio >= FUZZY_MIN_SCORE:
        return _Candidate(question, "fuzzy", ratio)
    return None


def _try_semantic(answer: Answer, candidate_questions: list[Question]) -> _Candidate | None:
    if not candidate_questions:
        return None

    try:
        raw = vision_service.run_structured_extraction(
            system_prompt=mapping_prompt.SYSTEM_PROMPT,
            user_prompt=mapping_prompt.build_user_prompt(
                answer.text,
                answer.detected_question_number,
                [{"number": q.number, "text": q.text} for q in candidate_questions],
            ),
            pages=[],
            tool_name=mapping_prompt.TOOL_NAME,
            tool_description=mapping_prompt.TOOL_DESCRIPTION,
            input_schema=mapping_prompt.INPUT_SCHEMA,
            max_tokens=512,
        )
    except vision_service.VisionServiceError:
        return None

    matched_number = raw.get("matched_question_number")
    confidence = raw.get("confidence", 0)
    if not matched_number:
        return None

    for q in candidate_questions:
        if q.number == matched_number:
            score = max(SEMANTIC_MIN_SCORE, min(1.0, confidence))
            return _Candidate(q, "semantic", score)
    return None


def run(questions: list[Question], answers: list[Answer], enable_semantic: bool = True) -> list[Mapping]:
    remaining_questions: list[Question] = list(questions)
    matched_question_ids: set[int] = set()
    mappings: list[Mapping] = []
    unmatched_answers: list[Answer] = []

    for answer in answers:
        best: _Candidate | None = None

        for question in remaining_questions:
            if id(question) in matched_question_ids:
                continue
            candidate = _try_exact_and_normalized(question, answer)
            if candidate and (best is None or candidate.score > best.score):
                best = candidate

        if best is None:
            for question in remaining_questions:
                if id(question) in matched_question_ids:
                    continue
                candidate = _try_fuzzy(question, answer)
                if candidate and candidate.score >= FUZZY_ACCEPT_SCORE:
                    if best is None or candidate.score > best.score:
                        best = candidate

        if best is not None:
            matched_question_ids.add(id(best.question))
            level = best.level if best.score >= LOW_CONFIDENCE_THRESHOLD else "low-confidence"
            mappings.append(
                Mapping(
                    question_number=best.question.number,
                    answer_question_number=answer.detected_question_number,
                    match_level=level,
                    match_score=best.score,
                    question=best.question,
                    answer=answer,
                )
            )
        else:
            unmatched_answers.append(answer)

    if enable_semantic and unmatched_answers:
        for answer in unmatched_answers[:]:
            candidates = [q for q in remaining_questions if id(q) not in matched_question_ids]
            semantic_match = _try_semantic(answer, candidates)
            if semantic_match is not None:
                matched_question_ids.add(id(semantic_match.question))
                level = (
                    semantic_match.level
                    if semantic_match.score >= LOW_CONFIDENCE_THRESHOLD
                    else "low-confidence"
                )
                mappings.append(
                    Mapping(
                        question_number=semantic_match.question.number,
                        answer_question_number=answer.detected_question_number,
                        match_level=level,
                        match_score=semantic_match.score,
                        question=semantic_match.question,
                        answer=answer,
                    )
                )
                unmatched_answers.remove(answer)

    for answer in unmatched_answers:
        mappings.append(
            Mapping(
                question_number=None,
                answer_question_number=answer.detected_question_number,
                match_level="unmatched",
                match_score=0.0,
                question=None,
                answer=answer,
            )
        )

    for question in remaining_questions:
        if id(question) not in matched_question_ids:
            mappings.append(
                Mapping(
                    question_number=question.number,
                    answer_question_number=None,
                    match_level="unanswered",
                    match_score=0.0,
                    question=question,
                    answer=None,
                )
            )

    return mappings
