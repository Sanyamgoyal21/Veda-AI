"""
Used only as a last-resort semantic matcher (Level 4) when an answer's
detected question number could not be matched to any question via exact,
normalized, or fuzzy string matching. The model is shown the remaining
unmatched questions and one unmatched answer, and asked whether the answer's
CONTENT plausibly responds to one of them.
"""

SYSTEM_PROMPT = """You are matching a single handwritten student answer to the
most plausible question it responds to, based purely on subject-matter
content, because number-based matching already failed.

Only propose a match if the answer content clearly and specifically responds
to one of the candidate questions. If no candidate is a clear content match,
say so explicitly rather than guessing.
"""

TOOL_NAME = "propose_match"

TOOL_DESCRIPTION = "Propose the best matching question number for this answer, or none."

INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "matched_question_number": {
            "type": ["string", "null"],
            "description": "The `number` field of the best matching candidate question, or null if none match.",
        },
        "confidence": {"type": "number", "description": "0 to 1"},
        "reasoning": {"type": "string"},
    },
    "required": ["matched_question_number", "confidence", "reasoning"],
}


def build_user_prompt(answer_text: str, detected_number: str, candidates: list[dict]) -> str:
    candidate_lines = "\n".join(
        f"- number: {c['number']!r} | text: {c['text'][:300]}" for c in candidates
    )
    return (
        f"Handwritten answer (detected number '{detected_number}', which did not "
        f"match any question number):\n\"{answer_text[:1500]}\"\n\n"
        f"Candidate unmatched questions:\n{candidate_lines}\n\n"
        "Call propose_match with the best candidate's `number`, or null if none "
        "of these candidates are a plausible content match."
    )
