"""
Deterministic test for EXIF-based rotation correction on uploaded photos.
No AI calls. Uses PIL's own EXIF writer (no extra dependency needed) to
create a genuinely EXIF-tagged JPEG, so this exercises the real code path
rather than asserting on a mock.
"""
import os
import tempfile

from PIL import Image

from app.services.pdf_service import load_document_pages


def _make_exif_rotated_jpeg(path: str, orientation: int, size=(200, 100)):
    """Writes a JPEG whose raw pixel data is `size`, tagged with an EXIF
    orientation that requires correction to display properly."""
    img = Image.new("RGB", size, color="white")
    exif = img.getexif()
    exif[0x0112] = orientation
    img.save(path, format="JPEG", exif=exif)


def test_exif_orientation_6_is_corrected():
    # Orientation 6: raw pixels are landscape (200x100) but must be rotated
    # 90deg to display correctly, i.e. the corrected image should be portrait.
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "sideways.jpg")
        _make_exif_rotated_jpeg(path, orientation=6, size=(200, 100))

        pages = load_document_pages(path)
        assert len(pages) == 1
        corrected_width, corrected_height = pages[0].image.size
        assert (corrected_width, corrected_height) == (100, 200), (
            "EXIF orientation 6 must rotate a 200x100 raw image to 100x200"
        )


def test_exif_orientation_1_unchanged():
    # Orientation 1 = "normal", no correction needed.
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "normal.jpg")
        _make_exif_rotated_jpeg(path, orientation=1, size=(200, 100))

        pages = load_document_pages(path)
        assert pages[0].image.size == (200, 100)


def test_image_without_exif_still_loads():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "no_exif.png")
        Image.new("RGB", (150, 80), color="white").save(path, format="PNG")

        pages = load_document_pages(path)
        assert pages[0].image.size == (150, 80)
