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
