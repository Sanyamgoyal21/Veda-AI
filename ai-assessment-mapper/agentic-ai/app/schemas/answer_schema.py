from pydantic import BaseModel, Field


class AnswerRegion(BaseModel):
    page: int = Field(ge=1)
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)


class Answer(BaseModel):
    detected_question_number: str
    normalized_question_number: str
    text: str
    confidence: float = Field(ge=0, le=1)
    regions: list[AnswerRegion]


class AnswerExtractionResult(BaseModel):
    answers: list[Answer]
    page_count: int
    warnings: list[str] = Field(default_factory=list)
