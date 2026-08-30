from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class AnswerRegion(BaseModel):
    page: int = Field(ge=1)
    # `page` is always the original PDF page.  Keep the explicit alias in
    # API output so a future blank-page filter cannot silently renumber it.
    original_page: Optional[int] = Field(default=None, ge=1)
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


SegmentType = Literal[
    "ANSWER_START", "SUBPART", "DIAGRAM_LABEL", "MATHEMATICAL_LABEL",
    "TEXT_FRAGMENT", "CONTINUATION", "UNKNOWN",
]


class AnswerSegment(BaseModel):
    id: str
    page: int = Field(ge=1)
    original_page: int = Field(ge=1)
    text: str = ""
    detected_question_number: Optional[str] = None
    normalized_question_number: str = ""
    question_number_confidence: float = Field(default=0, ge=0, le=1)
    bbox: AnswerRegion
    segment_confidence: float = Field(default=0.5, ge=0, le=1)
    segment_type: SegmentType = "UNKNOWN"
    continuation_likely: bool = False
    continuation_confidence: float = Field(default=0, ge=0, le=1)
    visual_order: int = Field(default=0, ge=0)
    has_diagram: bool = False
    has_handwriting: bool = True


class Answer(BaseModel):
    id: str = ""
    detected_question_number: str
    normalized_question_number: str
    text: str
    confidence: float = Field(ge=0, le=1)
    regions: list[AnswerRegion]
    pages: list[int] = Field(default_factory=list)
    # True when any constituent segment contained a diagram - lets grading
    # know a cropped answer image may include a diagram to evaluate, not
    # just handwritten text.
    has_diagram: bool = False


class AnswerExtractionResult(BaseModel):
    answers: list[Answer]
    page_count: int
    warnings: list[str] = Field(default_factory=list)
