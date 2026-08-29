"""Deterministic bounding-box validation tests. No AI calls."""
import pytest
from pydantic import ValidationError

from app.schemas.answer_schema import AnswerRegion
from app.schemas.question_schema import QuestionBoundingBox


def test_valid_region_accepted():
    region = AnswerRegion(page=1, x=0.1, y=0.1, width=0.5, height=0.2)
    assert region.area == pytest.approx(0.1)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"page": 1, "x": 0.8, "y": 0.1, "width": 0.5, "height": 0.1},  # x + width > 1
        {"page": 1, "x": 0.1, "y": 0.8, "width": 0.1, "height": 0.5},  # y + height > 1
        {"page": 1, "x": -0.1, "y": 0.1, "width": 0.5, "height": 0.1},  # negative x
        {"page": 0, "x": 0.1, "y": 0.1, "width": 0.5, "height": 0.1},  # page < 1
    ],
)
def test_impossible_regions_rejected(kwargs):
    with pytest.raises(ValidationError):
        AnswerRegion(**kwargs)


def test_region_exactly_at_page_edge_is_allowed():
    # x + width == 1 exactly should not be rejected (only genuinely > 1 is).
    region = AnswerRegion(page=1, x=0.5, y=0.5, width=0.5, height=0.5)
    assert region.x + region.width == 1.0


def test_question_bounding_box_same_rules():
    with pytest.raises(ValidationError):
        QuestionBoundingBox(page=1, x=0.9, y=0.1, width=0.5, height=0.1)

    box = QuestionBoundingBox(page=1, x=0.1, y=0.1, width=0.3, height=0.1)
    assert box.x + box.width <= 1.0
