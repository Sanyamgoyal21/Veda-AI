"""
One-off generator for the synthetic evaluation-dataset fixtures under
test-data/case_*/. Kept around (not deleted after first run) so the dataset
is easy to extend later - add an entry to CASES and re-run.

Usage:
    cd agentic-ai
    venv/Scripts/python.exe test-data/generate_cases.py
"""
import json
import os

BASE = os.path.dirname(__file__)


def region(page, x=0.1, y=0.1, width=0.5, height=0.1):
    return {"page": page, "x": x, "y": y, "width": width, "height": height}


def q(number, text, page=1, marks=None):
    d = {"number": number, "text": text, "page": page}
    if marks is not None:
        d["marks"] = marks
    return d


def a(detected, text, regions=None, confidence=0.9):
    return {
        "detected_question_number": detected,
        "text": text,
        "confidence": confidence,
        "regions": regions or [region(1)],
    }


CASES = {
    "case_normal_ordered": {
        "questions": [q("1", "Define velocity.", marks=2), q("2", "Define acceleration.", marks=2), q("3", "State the SI unit of force.", marks=1)],
        "answers": [
            a("1", "Velocity is the rate of change of displacement.", [region(1, y=0.1)]),
            a("2", "Acceleration is the rate of change of velocity.", [region(1, y=0.25)]),
            a("3", "Newton (N).", [region(1, y=0.4)]),
        ],
        "expected": {"expectedMappings": {"1": "1", "2": "2", "3": "3"}},
    },
    "case_subparts_abc": {
        "questions": [q("4", "Chemistry:"), q("4(a)", "Name an acid.", marks=1), q("4(b)", "Name a base.", marks=1), q("4(c)", "Name a salt.", marks=1)],
        "answers": [
            a("4(a)", "Hydrochloric acid.", [region(1, y=0.1)]),
            a("4(b)", "Sodium hydroxide.", [region(1, y=0.25)]),
            a("4(c)", "Sodium chloride.", [region(1, y=0.4)]),
        ],
        "expected": {"expectedMappings": {"4(a)": "4(a)", "4(b)": "4(b)", "4(c)": "4(c)"}, "expectedUnmatchedCount": 0},
    },
    "case_nested_subparts": {
        "questions": [q("5(a)(i)", "Define momentum.", marks=1), q("5(a)(ii)", "Give its SI unit.", marks=1)],
        "answers": [
            a("5(a)(i)", "Momentum is mass times velocity.", [region(1, y=0.1)]),
            a("5(a)(ii)", "kg m/s.", [region(1, y=0.25)]),
        ],
        "expected": {"expectedMappings": {"5(a)(i)": "5(a)(i)", "5(a)(ii)": "5(a)(ii)"}},
    },
    "case_multiple_nested_subparts": {
        "questions": [
            q("6(a)(i)", "State Ohm's law.", marks=1),
            q("6(a)(ii)", "Give the formula.", marks=1),
            q("6(b)(i)", "Define resistance.", marks=1),
        ],
        "answers": [
            a("6(a)(i)", "Voltage is proportional to current at constant temperature.", [region(1, y=0.1)]),
            a("6(a)(ii)", "V = IR.", [region(1, y=0.25)]),
            a("6(b)(i)", "Resistance opposes the flow of current.", [region(1, y=0.4)]),
        ],
        "expected": {"expectedMappings": {"6(a)(i)": "6(a)(i)", "6(a)(ii)": "6(a)(ii)", "6(b)(i)": "6(b)(i)"}},
    },
    "case_unanswered_question": {
        "questions": [q("7", "Define work.", marks=2), q("8", "Define power.", marks=2)],
        "answers": [a("7", "Work is force times displacement.", [region(1, y=0.1)])],
        "expected": {"expectedMappings": {"7": "7", "8": None}},
    },
    "case_unmatched_answer": {
        "questions": [q("9", "Define energy.", marks=2)],
        "answers": [
            a("9", "Energy is the capacity to do work.", [region(1, y=0.1)]),
            a("77", "This answer belongs to no question on this paper.", [region(1, y=0.25)]),
        ],
        "expected": {"expectedMappings": {"9": "9"}, "expectedUnmatchedAnswerIds": ["77"]},
    },
    "case_fuzzy_question_number": {
        # "a" misread as "4" - a common handwriting/vision confusion.
        "questions": [q("10(a)", "Name the powerhouse of the cell.", marks=1)],
        "answers": [a("10(4)", "Mitochondria.", [region(1)], confidence=0.65)],
        "expected": {"expectedMappings": {"10(a)": "10(4)"}},
    },
    "case_similar_looking_numbers": {
        # Guards against "1" being confused with "11" or "111".
        "questions": [q("1", "Q one.", marks=1), q("11", "Q eleven.", marks=1), q("111", "Q one-eleven.", marks=1)],
        "answers": [
            a("1", "Answer to one.", [region(1, y=0.1)]),
            a("11", "Answer to eleven.", [region(1, y=0.25)]),
            a("111", "Answer to one-eleven.", [region(1, y=0.4)]),
        ],
        "expected": {"expectedMappings": {"1": "1", "11": "11", "111": "111"}},
    },
    "case_multi_page_answer": {
        "questions": [q("12", "Explain the water cycle in detail.", marks=4)],
        "answers": [a("12", "Evaporation, condensation, and precipitation form a continuous cycle...",
                       [region(2, y=0.1, height=0.3), region(3, y=0.1, height=0.2)])],
        "expected": {"expectedMappings": {"12": "12"}, "multiPageQuestions": ["12"]},
    },
    "case_answer_crossing_chunk_boundary": {
        # Represents the post-merge shape of an answer that spanned a
        # chunking boundary (chunk-level merge itself is unit-tested
        # directly in test_extraction_merge.py) - this confirms mapping
        # still handles the resulting multi-region answer correctly.
        "questions": [q("13", "Describe the process of photosynthesis with equations.", marks=5)],
        "answers": [a("13", "Photosynthesis uses light energy to convert CO2 and water into glucose...",
                       [region(5, y=0.7, height=0.3), region(6, y=0.0, height=0.4)])],
        "expected": {"expectedMappings": {"13": "13"}, "multiPageQuestions": ["13"]},
    },
    "case_multiple_answers_one_page": {
        "questions": [q("14", "Name a metal.", marks=1), q("15", "Name a non-metal.", marks=1)],
        "answers": [
            a("14", "Iron.", [region(1, y=0.1, height=0.05)]),
            a("15", "Oxygen.", [region(1, y=0.2, height=0.05)]),
        ],
        "expected": {"expectedMappings": {"14": "14", "15": "15"}},
    },
    "case_multiple_questions_one_page": {
        "questions": [q("16", "Name a gas.", page=1, marks=1), q("17", "Name a liquid.", page=1, marks=1)],
        "answers": [
            a("16", "Nitrogen.", [region(1, y=0.1)]),
            a("17", "Water.", [region(1, y=0.25)]),
        ],
        "expected": {"expectedMappings": {"16": "16", "17": "17"}},
    },
    "case_continuation_pages": {
        # Represents a "Q18 continued" page whose extraction has already
        # been normalized/merged to the bare number (see
        # test_normalization.py for the "Q5 continued" -> "5" guarantee, and
        # test_extraction_merge.py for the merge itself).
        "questions": [q("18", "Describe the structure of an atom in detail.", marks=4)],
        "answers": [a("18", "An atom consists of a nucleus containing protons and neutrons... (continued) ...surrounded by electron shells.",
                       [region(7, y=0.6, height=0.4), region(8, y=0.0, height=0.3)])],
        "expected": {"expectedMappings": {"18": "18"}, "multiPageQuestions": ["18"]},
    },
    "case_poor_handwriting": {
        # Low transcription confidence must not block a structurally clear
        # number match - confidence and matchability are separate concerns.
        "questions": [q("19", "Define pH.", marks=2)],
        "answers": [a("19", "pH is a mesure of acidty or alkalinty of a solushun.", [region(1)], confidence=0.32)],
        "expected": {"expectedMappings": {"19": "19"}},
    },
    "case_blank_page": {
        "questions": [q("20", "Define reflection.", marks=2), q("21", "Define refraction.", marks=2)],
        "answers": [a("20", "Reflection is the bouncing back of light.", [region(1, y=0.1)])],
        "expected": {"expectedMappings": {"20": "20", "21": None}},
    },
    "case_extra_handwritten_notes": {
        "questions": [q("22", "Define diffusion.", marks=2)],
        "answers": [
            a("22", "Diffusion is the movement of particles from high to low concentration.", [region(1, y=0.1)]),
            a("doodle", "remember to ask teacher about the field trip", [region(1, y=0.8, height=0.05)]),
        ],
        "expected": {"expectedMappings": {"22": "22"}, "expectedUnmatchedAnswerIds": ["doodle"]},
    },
    "case_duplicate_looking_answer_numbers": {
        # The student answered the same question twice by mistake - the
        # first attempt wins, the second is surfaced as unmatched rather
        # than silently overwriting or being dropped.
        "questions": [q("23", "Define inertia.", marks=2)],
        "answers": [
            a("23", "First attempt: inertia resists change in motion.", [region(1, y=0.1)]),
            a("23", "Second attempt (crossed out first): inertia is a property of mass.", [region(1, y=0.3)]),
        ],
        "expected": {"expectedMappings": {"23": "23"}, "expectedUnmatchedCount": 1},
    },
    "case_missing_question_number": {
        # No number at all was legible - only the semantic fallback (mocked
        # here) can resolve it.
        "questions": [q("24", "Explain Newton's second law of motion.", marks=3), q("25", "Explain Newton's third law of motion.", marks=3)],
        "answers": [a("", "For every action there is an equal and opposite reaction.", [region(1)], confidence=0.4)],
        "expected": {
            "expectedMappings": {"24": None, "25": ""},
            "mockSemantic": {"matched_question_number": "25", "confidence": 0.75, "reasoning": "content matches Newton's third law"},
        },
    },
    "case_ambiguous_question_number": {
        # Content is too generic for even semantic matching to confidently
        # decide - the mock simulates the model correctly declining to
        # guess, which must result in "unmatched", never a forced pick.
        "questions": [q("26", "Explain photosynthesis.", marks=3), q("27", "Explain cellular respiration.", marks=3)],
        "answers": [a("2?", "This process is important for living things and involves energy.", [region(1)], confidence=0.3)],
        "expected": {
            "expectedMappings": {"26": None, "27": None},
            "expectedUnmatchedAnswerIds": ["2?"],
            "mockSemantic": {"matched_question_number": None, "confidence": 0.0, "reasoning": "too generic to confidently match either question"},
        },
    },
}


def main():
    for name, spec in CASES.items():
        case_dir = os.path.join(BASE, name)
        os.makedirs(case_dir, exist_ok=True)

        with open(os.path.join(case_dir, "questions.json"), "w") as f:
            json.dump({"questions": spec["questions"]}, f, indent=2)
        with open(os.path.join(case_dir, "answers.json"), "w") as f:
            json.dump({"answers": spec["answers"]}, f, indent=2)
        with open(os.path.join(case_dir, "expected_mappings.json"), "w") as f:
            json.dump(spec["expected"], f, indent=2)

        print(f"wrote {name}")

    print(f"\n{len(CASES)} cases generated.")


if __name__ == "__main__":
    main()
