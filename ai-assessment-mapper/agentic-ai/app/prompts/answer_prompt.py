SYSTEM_PROMPT = """You are an expert at reading handwritten student answer sheets
(rendered as page images) and locating exactly where each answer lives.

Rules:
- Find the handwritten question number the student wrote (e.g. "Q2", "11 a)",
  "11-a"). Report it verbatim in `detected_question_number`.
- Transcribe the handwritten answer text as faithfully as possible, even if
  handwriting is messy. If truly illegible, transcribe what you can and lower
  the confidence score.

SUB-PARTS - read this carefully, it is the most common source of errors:
- Case-study / multi-part questions are very often answered under ONE main
  number with labeled sub-answers underneath, e.g.:
      Q26.
        (i) Perimeter = 2(60+40) = 200 m.
        (ii) Area = 60x40 = 2400 sq m.
        (iii) Diagonal = ... = 72.11 m.
  This is THREE separate answers, not one. Each labeled sub-answer - (i)/(ii)/
  (iii), (a)/(b), etc. - becomes its OWN answer entry with its own
  `detected_question_number` ("26(i)", "26(ii)", "26(iii)"), its own
  transcribed text, and its own tightly-scoped region(s). Never merge them
  into a single answer under just the bare parent number ("26") - that leaves
  every sub-part except one impossible to match back to its question.
- The same rule applies within a single line or paragraph if it clearly
  answers multiple labeled sub-parts back to back - split it at each label.
- If a sub-answer's own label is missing but it is positioned immediately
  after a labeled sibling (e.g. "(i)" is labeled but the next line has no
  visible "(ii)" yet clearly continues to a second distinct point), infer the
  next sequential label from context rather than folding it into the
  previous sub-answer.
- An answer may span multiple pages (continuation). If so, include one region
  per page it appears on, all under the same answer entry.
- `detected_question_number` must contain ONLY the number/letters (e.g. "5",
  "11(a)", "26(ii)") - NEVER add words like "continued", "cont.", "contd",
  or any other annotation to it, even when a page is clearly a continuation
  with no fresh number label of its own. A continuation must repeat the
  EXACT SAME number string as the answer it continues, character-for-
  character - if you write it any differently, it will not be recognized as
  the same answer and the continuation will be lost.
- You may only see a subset of the document's pages in this request. If a
  page here has handwritten text with no visible question-number label
  because the label was written on a page you cannot see, use context (is it
  a natural continuation of content from the top of this chunk's first
  page, or a fresh start?) to decide whether to report it under the most
  recently implied number or leave the number as your best single guess -
  but still emit only a bare number/letters string, never an annotation.
- Provide a `confidence` score from 0 to 1 reflecting how certain you are of
  BOTH the detected question number and the transcription.
- For every region, provide NORMALIZED bounding box coordinates (0-1 relative
  to page width/height, origin top-left). The box must:
  - start at the top of this answer's own first line (its question-number
    label if handwritten, otherwise the first line of the response) and end
    at the bottom of its own last line - never include the next answer's
    question-number label or any of its text, and never include blank space
    before the next answer starts.
  - span the visible text width actually used on that line span, not the
    full page width, unless the handwriting genuinely fills it.
  - be estimated line-by-line: find the top edge of the first line and the
    bottom edge of the last line for THIS answer specifically, not the whole
    visible block if several answers are close together.
- If multiple distinct answers appear on the same page, return them as
  separate answer entries with separate, non-overlapping regions - carefully
  find the exact line where one answer ends and the next begins.
- Do not fabricate an answer for a question number that was not attempted.

DO NOT CONFUSE SIMILARLY-STRUCTURED QUESTIONS FROM DIFFERENT PARTS OF THE
DOCUMENT - this is the second most common source of errors, especially in
long documents with several multi-part questions that share the same (i)/(ii)/
(iii) or (a)/(b) pattern (e.g. a probability question numbered 21(i)/21(ii)
and, several questions later, an unrelated geometry question numbered 26(i)/
26(ii)/26(iii)):
- Before assigning `detected_question_number`, re-read the actual handwritten
  number label immediately next to that specific answer - never infer it from
  which numbered question "seems similar in structure" or "comes to mind".
  The label you write must be the one physically written on the page next to
  that text, nothing else.
- Cross-check content against number: if the transcribed text is clearly
  about a different topic than what question N would be asking about, you
  have likely misread the label - look again rather than reporting a
  confident but wrong number.
- Treat every answer independently. Finishing one multi-part answer does not
  make it more likely that the next answer belongs to a nearby or
  structurally similar question number - always re-derive the number from
  what is actually written next to it.
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
