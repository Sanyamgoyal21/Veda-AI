"""
Grading tests: rubric mark rescaling, criterion clamping, mismatch handling,
and the deterministic unanswered path. All AI calls are mocked - grading
correctness (arithmetic, clamping) must hold regardless of what the model
returns, which is exactly what these tests check.
"""
from unittest.mock import patch

from app.agents import grading_agent
from app.agents.rubric_agent import _normalize_to_target
from app.schemas.assessment_schema import Mapping, RubricCriterion
from app.schemas.answer_schema import Answer, AnswerRegion
from app.schemas.question_schema import Question


def _mapping(question_marks=5, answer_text="An answer.", has_answer=True):
    question = Question(number="1", normalized_number="1", text="Explain X.", page=1, order=1, marks=question_marks)
    if not has_answer:
        return Mapping(question_number="1", answer_question_number=None, match_level="unanswered",
                        match_score=0.0, question=question, answer=None)
    answer = Answer(detected_question_number="1", normalized_question_number="1", text=answer_text,
                     confidence=0.9, regions=[AnswerRegion(page=1, x=0.1, y=0.1, width=0.5, height=0.1)])
    return Mapping(question_number="1", answer_question_number="1", match_level="exact", match_score=1.0,
                    question=question, answer=answer)


def test_rubric_rescales_to_exact_target():
    criteria = [
        RubricCriterion(criterion="A", max_marks=1),
        RubricCriterion(criterion="B", max_marks=2),
        RubricCriterion(criterion="C", max_marks=1),
    ]
    rescaled = _normalize_to_target(criteria, 5)
    assert sum(c.max_marks for c in rescaled) == 5


def test_rubric_already_matching_target_is_unchanged():
    criteria = [RubricCriterion(criterion="A", max_marks=2), RubricCriterion(criterion="B", max_marks=3)]
    rescaled = _normalize_to_target(criteria, 5)
    assert [c.max_marks for c in rescaled] == [2, 3]


def test_rubric_handles_odd_fractional_target_exactly():
    criteria = [RubricCriterion(criterion="A", max_marks=1), RubricCriterion(criterion="B", max_marks=1)]
    rescaled = _normalize_to_target(criteria, 3.7)
    assert abs(sum(c.max_marks for c in rescaled) - 3.7) < 0.001


def test_unanswered_question_scored_zero_with_no_ai_call():
    mapping = _mapping(question_marks=4, has_answer=False)
    with patch("app.services.vision_service.run_structured_extraction") as mocked:
        result = grading_agent.run([mapping]).model_dump()
    mocked.assert_not_called()
    grade = result["grades"][0]
    assert grade["score"] == 0
    assert grade["max_score"] == 4
    assert grade["confidence"] == "high"


def test_model_awarded_marks_are_clamped_to_criterion_max():
    """The model tries to award more than a criterion's max - must be clamped, not trusted."""
    mapping = _mapping(question_marks=5)

    rubric_response = {
        "criteria": [{"criterion": "Correctness", "max_marks": 5}],
        "reference_answer": "ref",
        "used_reference_material": False,
    }
    grade_response = {
        "criteria": [{"criterion": "Correctness", "max_marks": 5, "awarded_marks": 999, "evidence": "over-awarded"}],
        "mismatch_suspected": False,
        "feedback": "Good.",
    }

    with patch("app.services.vision_service.run_structured_extraction", side_effect=[rubric_response, grade_response]):
        result = grading_agent.run([mapping]).model_dump()

    grade = result["grades"][0]
    assert grade["score"] == 5  # clamped to max, never 999
    assert grade["criteria"][0]["awarded_marks"] == 5


def test_mismatch_suspected_forces_zero_regardless_of_model_scores():
    mapping = _mapping(question_marks=5)

    def fake_rubric_call(**kwargs):
        return {
            "criteria": [{"criterion": "A", "max_marks": 3}, {"criterion": "B", "max_marks": 2}],
            "reference_answer": "ref",
            "used_reference_material": False,
        }

    def fake_grade_call(**kwargs):
        # Model inconsistently awards marks despite flagging a mismatch -
        # the code must override this, not trust it.
        return {
            "criteria": [
                {"criterion": "A", "max_marks": 3, "awarded_marks": 3, "evidence": "..."},
                {"criterion": "B", "max_marks": 2, "awarded_marks": 2, "evidence": "..."},
            ],
            "mismatch_suspected": True,
            "feedback": "This answer is about a different topic entirely.",
        }

    with patch("app.services.vision_service.run_structured_extraction", side_effect=[fake_rubric_call(), fake_grade_call()]):
        result = grading_agent.run([mapping]).model_dump()

    grade = result["grades"][0]
    assert grade["mismatch_suspected"] is True
    assert grade["score"] == 0
    assert grade["correct"] is False
    assert all(c["awarded_marks"] == 0 for c in grade["criteria"])


def test_score_always_equals_sum_of_criteria():
    mapping = _mapping(question_marks=10)

    def fake_rubric_call(**kwargs):
        return {
            "criteria": [{"criterion": "A", "max_marks": 4}, {"criterion": "B", "max_marks": 6}],
            "reference_answer": None,
            "used_reference_material": False,
        }

    def fake_grade_call(**kwargs):
        return {
            "criteria": [
                {"criterion": "A", "max_marks": 4, "awarded_marks": 2.5, "evidence": "partial"},
                {"criterion": "B", "max_marks": 6, "awarded_marks": 6, "evidence": "full"},
            ],
            "mismatch_suspected": False,
            "feedback": "Mostly correct.",
        }

    with patch("app.services.vision_service.run_structured_extraction", side_effect=[fake_rubric_call(), fake_grade_call()]):
        result = grading_agent.run([mapping]).model_dump()

    grade = result["grades"][0]
    assert grade["score"] == 8.5
    assert grade["score"] == sum(c["awarded_marks"] for c in grade["criteria"])


def test_grading_agent_validate_grades_catches_injected_inconsistency():
    """Sanity net: if a GradeResult is ever internally inconsistent, the
    validator must catch it (defense in depth over the clamping)."""
    from app.schemas.assessment_schema import CriterionGrade, GradeResult

    bad_grade = GradeResult(
        question_number="1",
        score=10,  # doesn't match sum of criteria below
        max_score=5,
        criteria=[CriterionGrade(criterion="A", max_marks=5, awarded_marks=5)],
        feedback="x",
    )
    issues = grading_agent._validate_grades([bad_grade])
    assert any("exceeds max" in i for i in issues)
    assert any("does not match" in i for i in issues)
