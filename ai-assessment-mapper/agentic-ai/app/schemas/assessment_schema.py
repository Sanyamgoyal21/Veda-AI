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
    # "teacher" only ever gets set by the backend's manual-correction
    # endpoint, never by this service - the AI always proposes "ai".
    source: Literal["ai", "teacher"] = "ai"


class ValidationResult(BaseModel):
    valid: bool
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    stats: dict = Field(default_factory=dict)


class RubricCriterion(BaseModel):
    criterion: str
    max_marks: float = Field(ge=0)


class Rubric(BaseModel):
    question_number: str
    criteria: list[RubricCriterion]
    reference_answer: Optional[str] = None
    # "teacher" only when a teacher-provided marking scheme actually covered
    # this specific question; otherwise AI-generated, which should carry
    # lower grading confidence.
    source: Literal["ai", "teacher"] = "ai"


class CriterionGrade(BaseModel):
    criterion: str
    max_marks: float = Field(ge=0)
    awarded_marks: float = Field(ge=0)
    evidence: str = ""


GradingConfidence = Literal["high", "medium", "low"]


class GradeResult(BaseModel):
    question_number: str
    # score/max_score are always computed in Python from `criteria` (or the
    # deterministic 0 for an unanswered question) - never taken from the
    # model's own stated total, so they can never be wrong arithmetic.
    score: Optional[float] = None
    max_score: Optional[float] = None
    criteria: list[CriterionGrade] = Field(default_factory=list)
    rubric_source: Literal["ai", "teacher"] = "ai"
    confidence: GradingConfidence = "medium"
    feedback: str
    correct: Optional[bool] = None
    # True when the grader judged the matched answer to be addressing a
    # different question entirely (likely mislabeled during extraction),
    # rather than merely an incorrect attempt at this one.
    mismatch_suspected: bool = False


class GradingResult(BaseModel):
    grades: list[GradeResult]
    total_score: Optional[float] = None
    total_max_score: Optional[float] = None
    percentage: Optional[float] = None
    warnings: list[str] = Field(default_factory=list)


class AssessmentResult(BaseModel):
    questions: list[Question]
    answers: list[Answer]
    mappings: list[Mapping]
    validation: ValidationResult
    grading: Optional[GradingResult] = None
