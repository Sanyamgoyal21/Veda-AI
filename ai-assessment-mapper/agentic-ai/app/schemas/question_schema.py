from typing import Optional
from pydantic import BaseModel, Field, field_validator


class QuestionBoundingBox(BaseModel):
    page: int = Field(ge=1)
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(ge=0, le=1)
    height: float = Field(ge=0, le=1)

    @field_validator("width")
    @classmethod
    def validate_width(cls, v, info):
        x = info.data.get("x", 0)
        if x + v > 1.0001:
            raise ValueError("bounding box exceeds page width")
        return v

    @field_validator("height")
    @classmethod
    def validate_height(cls, v, info):
        y = info.data.get("y", 0)
        if y + v > 1.0001:
            raise ValueError("bounding box exceeds page height")
        return v


class Question(BaseModel):
    number: str
    normalized_number: str
    text: str
    marks: Optional[float] = None
    page: int = Field(ge=1)
    order: int
    bounding_box: Optional[QuestionBoundingBox] = None
    # True when a diagram/figure accompanies this question - the region
    # (see question_extraction_agent) is unioned with the model's own wider
    # guess rather than shrunk to the text alone, so precise text-matching
    # never crops the diagram out of the highlighted area.
    has_diagram: bool = False


class QuestionExtractionResult(BaseModel):
    questions: list[Question]
    page_count: int
    warnings: list[str] = Field(default_factory=list)
