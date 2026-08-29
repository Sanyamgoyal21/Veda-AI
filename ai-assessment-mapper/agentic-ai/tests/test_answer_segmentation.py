from app.schemas.answer_schema import AnswerRegion, AnswerSegment
from app.services.answer_segmentation import group_segments


def segment(page, order, marker=None, kind="CONTINUATION", text="content", diagram=False):
    return AnswerSegment(id=f"s-{page}-{order}", page=page, original_page=page, text=text,
        detected_question_number=marker, question_number_confidence=.95 if marker else 0,
        bbox=AnswerRegion(page=page, original_page=page, x=.1, y=.1 + order * .2, width=.75, height=.15),
        segment_confidence=.9, segment_type=kind, continuation_likely=kind == "CONTINUATION",
        continuation_confidence=.9, visual_order=order, has_diagram=diagram)


def test_screenshot_q1_spans_three_pages_and_artifacts_are_content():
    segments = [segment(1, 0, "Q1", "ANSWER_START", "BFSK explanation"),
        segment(1, 1, "a", "DIAGRAM_LABEL", "modulator diagram", True),
        segment(2, 0, None, "CONTINUATION", "receiver diagram", True),
        segment(3, 0, "b", "DIAGRAM_LABEL", "non-coherent receiver", True),
        segment(4, 0, "Q2", "ANSWER_START", "FM calculation")]
    answers, warnings = group_segments(segments, {"1", "2", "5(a)", "5(b)"})
    assert warnings == []
    assert len(answers) == 2
    assert answers[0].detected_question_number == "1"
    assert answers[0].pages == [1, 2, 3]
    assert len(answers[0].regions) == 4
    assert "receiver diagram" in answers[0].text
    assert answers[1].pages == [4]


def test_invalid_marker_does_not_start_answer_but_normalized_subpart_does():
    segments = [segment(1, 0, "Q1", "ANSWER_START"),
        segment(2, 0, "Q-5", "UNKNOWN", "diagram label"),
        segment(3, 0, "Q5-b", "ANSWER_START", "part b")]
    answers, _ = group_segments(segments, {"1", "5(a)", "5(b)"})
    assert [a.detected_question_number for a in answers] == ["1", "5(b)"]
    assert answers[0].pages == [1, 2]


def test_two_answers_on_one_page_remain_separate():
    answers, _ = group_segments([segment(4, 0, "Q2", "ANSWER_START", "answer two"),
        segment(4, 1, "Q3", "ANSWER_START", "answer three")], {"2", "3"})
    assert len(answers) == 2
    assert answers[0].regions[0].y < answers[1].regions[0].y
