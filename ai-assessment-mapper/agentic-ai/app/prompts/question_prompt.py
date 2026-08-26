SYSTEM_PROMPT = """You are an expert exam paper parser. You read printed question
papers (rendered as page images) and extract every question exactly as printed.

Rules:
- Preserve the exact printed question number, including sub-parts, e.g. "11(a)".
- Preserve the original order questions appear in the document.
- If a question has sub-parts (a), (b), (c) etc., extract each sub-part as its
  own separate question entry, numbered like "11(a)", "11(b)".
- Extract the full question text verbatim (OCR it faithfully).
- If marks are printed next to a question (e.g. "[5 marks]", "(10)"), extract
  them as a number in the `marks` field, otherwise omit it.
- Record the 1-indexed page number the question appears on.
- If you can identify roughly where the question text sits on the page,
  provide a bounding box in NORMALIZED coordinates (0-1 relative to page
  width/height, origin top-left). If unsure, omit the bounding box rather
  than guessing.
- Never invent questions that are not present in the document.
"""

TOOL_NAME = "extract_questions"

TOOL_DESCRIPTION = (
    "Return every question extracted from the question paper pages, in "
    "original document order."
)

INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "number": {
                        "type": "string",
                        "description": "Printed question number exactly as shown, e.g. '11(a)'",
                    },
                    "text": {"type": "string"},
                    "marks": {"type": "number"},
                    "page": {"type": "integer"},
                    "bounding_box": {
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
                "required": ["number", "text", "page"],
            },
        },
        "warnings": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Any issues encountered, e.g. illegible text, ambiguous numbering.",
        },
    },
    "required": ["questions"],
}


def build_user_prompt(page_count: int) -> str:
    return (
        f"The attached document has {page_count} page(s), each preceded by a "
        "'--- Page N ---' label. Extract every question from all pages in the "
        "order they appear. Call the extract_questions tool with the result."
    )
