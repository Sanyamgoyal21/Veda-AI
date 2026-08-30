"""
Regression tests for refine_text_region's word-span matching, targeting a
real bug found in production: on a single page holding several short
answers that share vocabulary (e.g. "a", "response", "reflex", "action"),
the old matched-count-only ranking let a loose match wander into a
NEIGHBORING answer's text (or even blank space below it) instead of the
correct, tightly-packed location. No AI calls - pure PyMuPDF text search
against a real generated PDF.
"""
import fitz
import pytest

from app.services.pdf_service import refine_text_region

ANSWERS = [
    "A reflex action is a quick response to a stimulus without conscious thinking.",
    "A voluntary action is a controlled response performed consciously by a person.",
    "A quick response to a stimulus is sometimes called a reflex arc reaction.",
]


@pytest.fixture
def multi_answer_pdf(tmp_path):
    """One page with three short answers stacked vertically, each sharing
    heavy vocabulary overlap with the others - the exact shape that
    triggered the real bug (four similar biology answers on one page)."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    y_positions = [100, 300, 500]
    for text, y in zip(ANSWERS, y_positions):
        page.insert_text((72, y), f"Q{y}. Answer: {text}", fontsize=12)
    path = tmp_path / "multi_answer.pdf"
    doc.save(str(path))
    doc.close()
    return str(path), y_positions


def _region_center_y_fraction(region):
    return region["y"] + region["height"] / 2


def test_each_answer_resolves_to_its_own_paragraph_not_a_neighbor(multi_answer_pdf):
    path, y_positions = multi_answer_pdf
    page_height = 792

    regions = [refine_text_region(path, 1, text) for text in ANSWERS]
    assert all(r is not None for r in regions), "every answer should find a confident match"

    centers = [_region_center_y_fraction(r) for r in regions]
    expected_fractions = [y / page_height for y in y_positions]

    # Each resolved region must land closest to ITS OWN paragraph's actual
    # y-position, not another answer's - this is the exact cross-
    # contamination the old matched-count-only ranking allowed.
    for i, center in enumerate(centers):
        distances = [abs(center - expected) for expected in expected_fractions]
        closest = distances.index(min(distances))
        assert closest == i, (
            f"answer {i} resolved nearest to paragraph {closest}'s position instead of its own"
        )

    # Regions must also be in the same top-to-bottom order as the answers
    # themselves (monotonically increasing y), not scrambled.
    assert centers == sorted(centers)


def test_no_region_lands_in_blank_space_below_all_text(multi_answer_pdf):
    path, _ = multi_answer_pdf
    for text in ANSWERS:
        region = refine_text_region(path, 1, text)
        assert region is not None
        # The page is 792pt tall with the last paragraph starting at y=500;
        # a correct match must never resolve below where any real text is.
        assert region["y"] < 560 / 792, "region drifted into blank space below all content"
