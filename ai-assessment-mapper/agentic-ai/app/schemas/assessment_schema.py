from typing import Literal, Optional
from pydantic import BaseModel, Field

from app.schemas.question_schema import Question
from app.schemas.answer_schema import Answer

MatchLevel = Literal[
    "exact",
    "normalized",
    "fuzzy",
    "semantic",
    "low-confidence",
    "unanswered",
    "unmatched",
]


class Mapping(BaseModel):
    question_number: Optional[str] = None
    answer_question_number: Optional[str] = None
    match_level: MatchLevel
    match_score: float = Field(ge=0, le=1)
    question: Optional[Question] = None
    answer: Optional[Answer] = None


class ValidationResult(BaseModel):
    valid: bool
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    stats: dict = Field(default_factory=dict)


class GradeResult(BaseModel):
    question_number: str
    score: Optional[float] = None
    max_score: Optional[float] = None
    feedback: str
    correct: Optional[bool] = None


class GradingResult(BaseModel):
    grades: list[GradeResult]
    total_score: Optional[float] = None
    total_max_score: Optional[float] = None
    percentage: Optional[float] = None


class AssessmentResult(BaseModel):
    questions: list[Question]
    answers: list[Answer]
    mappings: list[Mapping]
    validation: ValidationResult
    grading: Optional[GradingResult] = None
