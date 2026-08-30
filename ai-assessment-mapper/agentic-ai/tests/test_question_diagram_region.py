"""
Regression tests for diagram-aware bounding boxes on the question-paper
side: when a question is accompanied by a diagram/figure, its region must
span both the text and the diagram, not shrink to text-only once
refine_text_region finds a precise match for the text alone.
"""
from unittest.mock import patch

import fitz

from app.agents.question_extraction_agent import _union_bbox_dicts, run
from app.services.pdf_service import load_document_pages


def _fake_extraction_response(text, has_diagram, wide_bbox):
    return {"questions": [{
        "number": "1",
        "text": text,
        "page": 1,
        "has_diagram": has_diagram,
        "bounding_box": wide_bbox,
    }]}


def test_union_bbox_dicts_covers_both_inputs():
    a = {"page": 1, "x": 0.05, "y": 0.1, "width": 0.9, "height": 0.4}
    b = {"page": 1, "x": 0.1, "y": 0.15, "width": 0.2, "height": 0.05}
    union = _union_bbox_dicts(a, b)
    assert union["x"] == 0.05 and union["y"] == 0.1
    assert union["x"] + union["width"] >= a["x"] + a["width"]
    assert union["y"] + union["height"] >= a["y"] + a["height"]


def test_question_with_diagram_keeps_the_wider_region(tmp_path):
    text = "Study the circuit diagram below and calculate the total resistance."
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_textbox(fitz.Rect(50, 80, 560, 110), text, fontsize=11)
    path = tmp_path / "question_with_diagram.pdf"
    doc.save(str(path))
    doc.close()

    # The AI's own guess spans further down the page than the text alone -
    # it was told to include the diagram that follows the question text.
    wide_bbox = {"page": 1, "x": 0.05, "y": 0.1, "width": 0.9, "height": 0.4}
    pages = load_document_pages(str(path))

    with patch(
        "app.services.vision_service.run_structured_extraction",
        return_value=_fake_extraction_response(text, True, wide_bbox),
    ):
        result = run(pages, file_path=str(path))

    assert len(result.questions) == 1
    q = result.questions[0]
    assert q.has_diagram is True
    assert q.bounding_box is not None
    # Must still cover the AI's original wider guess, not shrink to the
    # matched text's own tight box.
    assert q.bounding_box.y <= wide_bbox["y"] + 0.01
    assert q.bounding_box.y + q.bounding_box.height >= wide_bbox["y"] + wide_bbox["height"] - 0.01


def test_question_without_diagram_gets_the_tight_refined_box(tmp_path):
    text = "Define Newton's second law of motion."
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_textbox(fitz.Rect(50, 80, 560, 110), text, fontsize=11)
    path = tmp_path / "question_no_diagram.pdf"
    doc.save(str(path))
    doc.close()

    wide_bbox = {"page": 1, "x": 0.05, "y": 0.1, "width": 0.9, "height": 0.4}
    pages = load_document_pages(str(path))

    with patch(
        "app.services.vision_service.run_structured_extraction",
        return_value=_fake_extraction_response(text, False, wide_bbox),
    ):
        result = run(pages, file_path=str(path))

    q = result.questions[0]
    assert q.has_diagram is False
    assert q.bounding_box.height < wide_bbox["height"] / 2
