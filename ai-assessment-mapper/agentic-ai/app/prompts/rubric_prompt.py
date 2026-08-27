SYSTEM_PROMPT = """You are an experienced teacher building a marking rubric for
one exam question, before seeing any student's answer.

Break the question into 2-5 concrete, gradable criteria that together cover
everything a complete answer should include (e.g. "Correct definition",
"Explains the underlying mechanism", "Gives a valid example",
"Correct final numeric answer", "Shows correct working/method"). Assign each
criterion a share of the question's total marks.

If reference material (a teacher-provided marking scheme or model answer) is
attached, and it actually covers this specific question, base the criteria
and reference answer on it directly and set `used_reference_material` to
true. If the attached material does not mention this question, or no
material is attached, generate the rubric and a concise reference answer
yourself from the question text alone, and set `used_reference_material` to
false - do not claim to have used material that doesn't address this
question.

The criteria's marks do not need to sum to exactly the total (the calling
code rescales them deterministically), but keep them roughly proportionate
to how much each part of a complete answer matters.
"""

TOOL_NAME = "build_rubric"
TOOL_DESCRIPTION = "Return a marking rubric (criteria + reference answer) for one question."

INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "criteria": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "criterion": {"type": "string"},
                    "max_marks": {"type": "number"},
                },
                "required": ["criterion", "max_marks"],
            },
        },
        "reference_answer": {
            "type": "string",
            "description": "A concise correct/expected answer to this question.",
        },
        "used_reference_material": {
            "type": "boolean",
            "description": "True only if attached teacher-provided material actually covered this question.",
        },
    },
    "required": ["criteria", "reference_answer", "used_reference_material"],
}


MAX_REFERENCE_TEXT_CHARS = 6000


def build_user_prompt(
    question_text: str,
    marks: float | None,
    reference_text: str | None = None,
    has_reference_images: bool = False,
) -> str:
    marks_line = f"Total marks for this question: {marks}." if marks else "No marks were printed for this question; assume a total of 5."

    if reference_text:
        reference_line = (
            "Teacher-provided marking scheme (full document text below) - check whether it "
            f"covers this question:\n\n{reference_text[:MAX_REFERENCE_TEXT_CHARS]}"
        )
    elif has_reference_images:
        reference_line = (
            "Teacher-provided marking scheme is attached as page images - "
            "check whether it covers this question."
        )
    else:
        reference_line = "No reference material was provided."

    return (
        f"Question:\n{question_text}\n\n"
        f"{marks_line}\n"
        f"{reference_line}\n\n"
        "Call build_rubric with the result."
    )
