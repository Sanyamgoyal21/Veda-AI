"""
The ONLY module in this codebase allowed to talk to the external vision AI
provider. Agents never import an AI SDK directly - they call functions here.

Swapping providers means editing this file only. The provider is selected via
AI_API_KEY / AI_MODEL environment variables and is never exposed to callers
outside this service, let alone to the frontend.

Currently backed by OpenAI's Chat Completions API (vision + forced
function-calling for structured output).
"""
import json
import os

import openai

from app.services.image_service import image_to_base64, resize_for_vision
from app.services.pdf_service import PageImage

AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o")

_client: openai.OpenAI | None = None


class VisionServiceError(Exception):
    """Raised when the vision provider fails or returns something unusable."""


def _get_client() -> openai.OpenAI:
    global _client
    if not AI_API_KEY:
        raise VisionServiceError(
            "AI_API_KEY is not configured on the agentic-ai service"
        )
    if _client is None:
        _client = openai.OpenAI(api_key=AI_API_KEY)
    return _client


def _pages_to_content_blocks(pages: list[PageImage]) -> list[dict]:
    blocks: list[dict] = []
    for page_image in pages:
        resized = resize_for_vision(page_image.image)
        encoded = image_to_base64(resized, fmt="JPEG")
        blocks.append({"type": "text", "text": f"--- Page {page_image.page} ---"})
        blocks.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
            }
        )
    return blocks


def run_structured_extraction(
    *,
    system_prompt: str,
    user_prompt: str,
    pages: list[PageImage],
    tool_name: str,
    tool_description: str,
    input_schema: dict,
    max_tokens: int = 8192,
) -> dict:
    """
    Sends a system + user prompt along with rendered page images to the
    vision model, forcing it to respond via a single structured function call
    so the output is always valid JSON matching `input_schema`.
    """
    client = _get_client()

    content = [{"type": "text", "text": user_prompt}] + _pages_to_content_blocks(pages)

    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": tool_description,
                        "parameters": input_schema,
                    },
                }
            ],
            tool_choice={"type": "function", "function": {"name": tool_name}},
        )
    except openai.APITimeoutError as exc:
        raise VisionServiceError("AI provider request timed out") from exc
    except openai.APIError as exc:
        raise VisionServiceError(f"AI provider error: {exc}") from exc

    tool_calls = response.choices[0].message.tool_calls
    if not tool_calls:
        raise VisionServiceError("AI provider did not return the expected tool call")

    try:
        return json.loads(tool_calls[0].function.arguments)
    except json.JSONDecodeError as exc:
        raise VisionServiceError("AI provider returned malformed JSON") from exc


def run_text_completion(*, system_prompt: str, user_prompt: str, max_tokens: int = 2048) -> str:
    """Plain text completion, used by the grading agent for free-form feedback."""
    client = _get_client()
    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except openai.APITimeoutError as exc:
        raise VisionServiceError("AI provider request timed out") from exc
    except openai.APIError as exc:
        raise VisionServiceError(f"AI provider error: {exc}") from exc

    return response.choices[0].message.content or ""
