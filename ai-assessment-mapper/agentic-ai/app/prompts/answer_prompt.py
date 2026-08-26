SYSTEM_PROMPT = """You are an expert at reading handwritten student answer sheets
(rendered as page images) and locating exactly where each answer lives.

Rules:
- Find the handwritten question number the student wrote (e.g. "Q2", "11 a)",
  "11-a"). Report it verbatim in `detected_question_number`.
- Transcribe the handwritten answer text as faithfully as possible, even if
  handwriting is messy. If truly illegible, transcribe what you can and lower
  the confidence score.
- An answer may span multiple pages (continuation). If so, include one region
  per page it appears on, all under the same answer entry.
- Provide a `confidence` score from 0 to 1 reflecting how certain you are of
  BOTH the detected question number and the transcription.
- For every region, provide NORMALIZED bounding box coordinates (0-1 relative
  to page width/height, origin top-left) tightly wrapping the handwritten
  answer region only (not the whole page).
- If multiple distinct answers appear on the same page, return them as
  separate answer entries with separate regions.
- Do not fabricate an answer for a question number that was not attempted.
"""

TOOL_NAME = "extract_answers"

TOOL_DESCRIPTION = (
    "Return every handwritten answer detected on the answer sheet pages, "
    "with the exact page region(s) it occupies."
)

INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "answers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "detected_question_number": {"type": "string"},
                    "text": {"type": "string"},
                    "confidence": {"type": "number"},
                    "regions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "page": {"type": "integer"},
                                "x": {"type": "number"},
                                "y": {"type": "number"},
                                "width": {"type": "number"},
                                "height": {"type": "number"},
                            },
                            "required": ["page", "x", "y", "width", "height"],
                        },
                    },
                },
                "required": ["detected_question_number", "text", "confidence", "regions"],
            },
        },
        "warnings": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["answers"],
}


def build_user_prompt(page_count: int) -> str:
    return (
        f"The attached answer sheet has {page_count} page(s), each preceded by a "
        "'--- Page N ---' label. Detect every handwritten answer across all pages "
        "and call the extract_answers tool with the result."
    )
