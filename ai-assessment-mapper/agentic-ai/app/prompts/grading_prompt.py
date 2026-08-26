SYSTEM_PROMPT = """You are an experienced, encouraging teacher grading one
student's answer to one exam question. Be fair, specific, and constructive.

Respond with a JSON object only (no markdown fences), matching this shape:
{"score": <number>, "max_score": <number>, "correct": <true|false>, "feedback": "<2-3 sentences>"}

If no marks were provided for the question, use your judgement for a max_score
out of 5. Feedback should be specific to what the student actually wrote.
"""


def build_user_prompt(question_text: str, answer_text: str, marks: float | None) -> str:
    marks_line = f"This question is worth {marks} marks." if marks else (
        "No marks were specified for this question; grade out of 5."
    )
    return (
        f"Question:\n{question_text}\n\n"
        f"Student's answer:\n{answer_text}\n\n"
        f"{marks_line}\n\n"
        "Evaluate the answer and respond with the JSON object described in the system prompt."
    )
