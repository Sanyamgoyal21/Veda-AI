import fitz

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


def test_diagram_answer_region_is_not_shrunk_to_text_only(tmp_path):
    """
    Reproduces a real bug: refine_text_region gives a precise box for the
    TEXT it was given, but a diagram drawn below/beside that text sits
    outside that box entirely - the old code replaced the region outright,
    silently cropping the diagram out of what gets highlighted (and later
    cropped for grading). When has_diagram is true, the region must instead
    be the union of the AI's own (wider) guess and the refined text box.
    """
    text = "A plant cell has a rigid outer cell wall and a cell membrane."
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_textbox(fitz.Rect(50, 80, 560, 110), text, fontsize=11)
    path = tmp_path / "diagram_answer.pdf"
    doc.save(str(path))
    doc.close()

    # The AI's own guess spans further down the page than the text alone -
    # it was told to include the diagram that follows the text.
    wide_guess = AnswerRegion(page=1, original_page=1, x=0.05, y=0.1, width=0.9, height=0.4)
    diagram_segment = AnswerSegment(
        id="s-1-0", page=1, original_page=1, text=text,
        detected_question_number="8", question_number_confidence=0.95,
        bbox=wide_guess, segment_confidence=0.9, segment_type="ANSWER_START",
        continuation_likely=False, continuation_confidence=0, visual_order=0, has_diagram=True,
    )

    answers, _ = group_segments([diagram_segment], {"8"}, str(path))
    assert len(answers) == 1
    region = answers[0].regions[0]

    # The region must still cover the AI's original wider guess (where the
    # diagram lives), not shrink down to just the matched text's tight box.
    assert region.y <= wide_guess.y + 0.01
    assert region.y + region.height >= wide_guess.y + wide_guess.height - 0.01
    assert answers[0].has_diagram is True


def test_text_only_answer_still_gets_the_tight_refined_box(tmp_path):
    """No diagram means no reason to keep the AI's looser original guess -
    the precise refined box should be used outright, same as before."""
    text = "Photosynthesis converts light energy into chemical energy."
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_textbox(fitz.Rect(50, 80, 560, 110), text, fontsize=11)
    path = tmp_path / "text_only_answer.pdf"
    doc.save(str(path))
    doc.close()

    wide_guess = AnswerRegion(page=1, original_page=1, x=0.05, y=0.1, width=0.9, height=0.4)
    segment_ = AnswerSegment(
        id="s-1-0", page=1, original_page=1, text=text,
        detected_question_number="1", question_number_confidence=0.95,
        bbox=wide_guess, segment_confidence=0.9, segment_type="ANSWER_START",
        continuation_likely=False, continuation_confidence=0, visual_order=0, has_diagram=False,
    )

    answers, _ = group_segments([segment_], {"1"}, str(path))
    region = answers[0].regions[0]

    # Refined box is tight to the text - much smaller than the AI's guess.
    assert region.height < wide_guess.height / 2
    assert answers[0].has_diagram is False
