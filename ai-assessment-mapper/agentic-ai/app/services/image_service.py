"""Image pre-processing helpers: downscaling and base64 encoding for the
vision model, and re-usable page metadata (pixel dimensions) that lets the
frontend map normalized bounding boxes back to any page.
"""
import base64
import io
import os

from PIL import Image

MAX_IMAGE_DIMENSION = int(os.getenv("MAX_IMAGE_DIMENSION", "1600"))


def resize_for_vision(image: Image.Image) -> Image.Image:
    width, height = image.size
    largest = max(width, height)
    if largest <= MAX_IMAGE_DIMENSION:
        return image

    scale = MAX_IMAGE_DIMENSION / largest
    new_size = (int(width * scale), int(height * scale))
    return image.resize(new_size, Image.LANCZOS)


def image_to_base64(image: Image.Image, fmt: str = "JPEG") -> str:
    buffer = io.BytesIO()
    if fmt == "JPEG" and image.mode != "RGB":
        image = image.convert("RGB")
    image.save(buffer, format=fmt, quality=85)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def media_type_for_format(fmt: str) -> str:
    return "image/jpeg" if fmt == "JPEG" else "image/png"


def crop_region(image: Image.Image, x: float, y: float, width: float, height: float, margin: float = 0.02) -> Image.Image:
    """
    Crops a page image to a normalized (0-1) region, with a small margin so
    the crop doesn't clip the edges of the handwriting. Used to give the
    grading model the actual answer image instead of only its transcription.
    """
    img_width, img_height = image.size
    x0 = max(0, int((x - margin) * img_width))
    y0 = max(0, int((y - margin) * img_height))
    x1 = min(img_width, int((x + width + margin) * img_width))
    y1 = min(img_height, int((y + height + margin) * img_height))
    if x1 <= x0 or y1 <= y0:
        return image
    return image.crop((x0, y0, x1, y1))
