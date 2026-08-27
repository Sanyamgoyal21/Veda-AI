SYSTEM_PROMPT = """You are an expert exam paper parser. You read printed question
papers (rendered as page images) and extract every question exactly as printed.

Rules:
- Preserve the exact printed question number, including sub-parts, e.g. "11(a)".
- Preserve the original order questions appear in the document.

SUB-PARTS - read this carefully, it is the most common source of errors:
- If a question is broken into labeled sub-parts - (a)/(b), (i)/(ii), or
  similarly - EVERY sub-part becomes its OWN separate question entry, numbered
  like "2(a)", "2(b)". Never merge a lettered sub-part's text into the bare
  parent number (e.g. never fold "(a)"'s content into a plain "2" entry while
  extracting "2(b)" separately - if (b) exists as a labeled part, (a) almost
  certainly does too, even if its label is easy to miss, e.g. printed close to
  the question stem, on the line right after "Q2.", or without a line break).
- Before finalizing, re-scan every question stem for anything that reads like
  two distinct sub-questions bundled together (e.g. "What is X? Explain Y with
  an example." often means "(a) What is X?" and "(b) Explain Y..." were
  printed as one block, or that a second lettered part follows and must not be
  dropped). If genuinely a single unlabeled question, keep it as one entry.
- Marks belong to whichever specific part they are printed next to. If each
  sub-part has its own bracketed mark value, record each part's own value in
  its own `marks` field - do not sum sub-part marks into the parent, and do
  not apply one part's marks to a sibling part.
- Do NOT also emit a separate entry for the bare parent number when its
  sub-parts already cover its content. A line like "Q2. Life Processes [5
  Marks]" followed by "(a) ... [3 Marks]" and "(b) ... [2 Marks]" is a
  section/topic label with no question of its own - only "2(a)" and "2(b)"
  are real, answerable questions; do not also output a "2" entry for it. Only
  keep a bare parent entry if it asks something itself, separately from and
  in addition to its lettered sub-parts.

- Extract the full question text verbatim (OCR it faithfully), for exactly
  the span belonging to that specific question/sub-part - do not include the
  next question's text.
- If marks are printed for a question, extract them as a number in the
  `marks` field, otherwise omit it.
- Record the 1-indexed page number the question appears on.
- If you can identify roughly where the question text sits on the page,
  provide a bounding box in NORMALIZED coordinates (0-1 relative to page
  width/height, origin top-left), tightly wrapping ONLY this question's own
  text - stop before the next question begins, don't include surrounding
  whitespace or neighboring questions. If unsure, omit the bounding box
  rather than guessing.
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
