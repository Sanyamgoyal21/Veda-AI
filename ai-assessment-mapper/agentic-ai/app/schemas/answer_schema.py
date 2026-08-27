from pydantic import BaseModel, Field, field_validator


class AnswerRegion(BaseModel):
    page: int = Field(ge=1)
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)

    @field_validator("width")
    @classmethod
    def validate_width(cls, v, info):
        x = info.data.get("x", 0)
        if x + v > 1.0001:
            raise ValueError("region exceeds page width (x + width > 1)")
        return v

    @field_validator("height")
    @classmethod
    def validate_height(cls, v, info):
        y = info.data.get("y", 0)
        if y + v > 1.0001:
            raise ValueError("region exceeds page height (y + height > 1)")
        return v

    @property
    def area(self) -> float:
        return self.width * self.height


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
