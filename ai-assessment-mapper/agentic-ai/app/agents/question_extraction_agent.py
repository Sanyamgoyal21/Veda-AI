"""Extracts every question from a question paper document."""
from collections import defaultdict
import re

from pydantic import ValidationError

from app.prompts import question_prompt
from app.schemas.question_schema import Question, QuestionBoundingBox, QuestionExtractionResult
from app.services import vision_service
from app.services.chunking import chunk_pages
from app.services.pdf_service import PageImage, refine_text_region
from app.utils.normalization import extract_order_key, normalize_question_number

_SUBPART_RE = re.compile(r"(?<!\w)\(([a-z]|i{1,4}|iv|v|vi{0,3}|ix|x)\)\s*", re.IGNORECASE)
_SINGLE_LETTER_PARENT_RE = re.compile(r"^(\d+)\(([a-z])\)$")


def _split_bundled_subparts(item: dict) -> list[dict]:
    """Split a bare parent item when the model bundled 2+ labeled parts."""
    number = normalize_question_number(item.get("number", ""))
    text = item.get("text", "")
    if not number or "(" in number:
        return [item]
    matches = list(_SUBPART_RE.finditer(text))
    if len(matches) < 2:
        return [item]

    stem = text[: matches[0].start()].strip(" :-\n")
    result = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        part_text = text[match.end() : end].strip(" ,;:-\n")
        if not part_text:
            return [item]
        result.append({
            **item,
            "number": f"{number}({match.group(1).lower()})",
            "text": f"{stem} {part_text}".strip(),
        })
    return result


def _extract_raw_items(pages: list[PageImage]) -> tuple[list[dict], list[str]]:
    """
    Runs extraction chunk-by-chunk (a single chunk for documents short enough
    to need no splitting) and returns every raw question item tagged with
    which chunk produced it, plus any warnings from each call.
    """
    chunks = chunk_pages(pages)
    items_with_chunk: list[dict] = []
    warnings: list[str] = []

    for chunk_index, chunk in enumerate(chunks):
        raw = vision_service.run_structured_extraction(
            system_prompt=question_prompt.SYSTEM_PROMPT,
            user_prompt=question_prompt.build_user_prompt(len(chunk.pages)),
            pages=chunk.pages,
            tool_name=question_prompt.TOOL_NAME,
            tool_description=question_prompt.TOOL_DESCRIPTION,
            input_schema=question_prompt.INPUT_SCHEMA,
        )
        warnings.extend(raw.get("warnings", []))
        for item in raw.get("questions", []):
            items_with_chunk.append({**item, "_chunk_index": chunk_index})

    return items_with_chunk, warnings


def _dedupe_across_chunks(items: list[dict]) -> tuple[list[dict], list[str]]:
    """
    Adjacent chunks share overlap pages, so the same question can be
    extracted twice (once by each chunk that can see it). Group by
    normalized number and keep only the most complete version - never
    silently merge two different questions that happen to share a number.
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        key = normalize_question_number(item.get("number", ""))
        groups[key].append(item)

    deduped: list[dict] = []
    warnings: list[str] = []

    for key, entries in groups.items():
        if len(entries) == 1 or not key:
            deduped.extend(entries)
            continue

        entries.sort(key=lambda e: len(e.get("text", "")), reverse=True)
        deduped.append(entries[0])
        warnings.append(
            f"Question '{entries[0].get('number')}' was seen in {len(entries)} overlapping "
            "chunks; kept the most complete extraction."
        )

    return deduped, warnings


# Verbs/wh-words that mark a clause as its own independent instruction or
# question, as opposed to a bare descriptive value. Deliberately excludes
# linking verbs ("is", "are", "has") - an MCQ stem is always a declarative
# setup ending in one of those ("...has:", "...roots are:"), never an
# instruction of its own.
_INSTRUCTION_WORD_RE = re.compile(
    r"\b(find|explain|name|define|state|describe|calculate|determine|prove|"
    r"show|solve|differentiate|draw|list|give|write|derive|justify|compare|"
    r"illustrate|identify|evaluate|construct|verify|distinguish|discuss|"
    r"analyse|analyze|compute|classify|outline|summarise|summarize|what|"
    r"how|why|when|where|which|who)\b",
    re.IGNORECASE,
)


def _shared_word_prefix_len(word_lists: list[list[str]]) -> int:
    """Number of leading words identical (case/punctuation-insensitive)
    across every text - word-aligned, so it never splits a shared prefix
    mid-word the way a character-level comparison could."""
    count = 0
    for words in zip(*word_lists):
        if len({w.lower().strip(".,;:!?") for w in words}) != 1:
            break
        count += 1
    return count


def _looks_like_mcq_options(texts: list[str]) -> bool:
    """
    Deterministic check for "these lettered items are answer OPTIONS for one
    question, not separate sub-questions" - e.g. splitting either of these
    into 4 items each is wrong, since a student answers an MCQ by picking
    ONE option, not by answering four questions:
        "The HCF of 96 and 404 is: (a) 4 (b) 8 (c) 12 (d) 16"
        "...has: (a) No solution (b) Unique solution (c) Infinitely many
         solutions (d) Exactly two solutions"

    True when every sibling shares most of its text (a common stem) AND the
    differing tail is a short descriptive value/phrase with no instruction
    verb of its own. The instruction-verb check (not just a word-count cap)
    is what makes this general enough for real MCQ phrasing instead of only
    matching bare-number options: genuinely distinct sub-questions that
    share a template stem - e.g. "Find the probability the sum is 7" vs
    "...is a prime number" - are caught because the shared stem itself
    contains "Find" (a real instruction repeated per sub-part), which an
    MCQ stem never does.
    """
    if len(texts) < 2:
        return False
    word_lists = [t.split() for t in texts]
    min_words = min(len(w) for w in word_lists)
    prefix_len = _shared_word_prefix_len(word_lists)
    if min_words == 0 or prefix_len == 0 or prefix_len / min_words < 0.5:
        return False

    prefix_text = " ".join(word_lists[0][:prefix_len])
    if _INSTRUCTION_WORD_RE.search(prefix_text):
        return False

    for words in word_lists:
        suffix_words = words[prefix_len:]
        if not suffix_words or len(suffix_words) > 8:
            return False
        if _INSTRUCTION_WORD_RE.search(" ".join(suffix_words)):
            return False
    return True


def _merge_mcq_option_siblings(items: list[dict]) -> tuple[list[dict], list[str]]:
    """
    Only ever merges a run of items whose numbers are the SAME parent with
    single-letter sub-parts labeled sequentially from 'a' (the standard MCQ/
    exam sub-part convention) - never touches roman-numeral labels like
    "(i)"/"(ii)" (which don't match the single-letter parent pattern at all,
    except the rare case a roman numeral IS a single letter like "(i)"
    itself; even then, a lone unmatched sibling never reaches the length>=2
    check below). Merging additionally requires the content itself to look
    like options (see _looks_like_mcq_options) - the label shape alone is
    never sufficient, since genuine sub-parts commonly use the same a/b/c/d
    labeling too.
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    others: list[dict] = []
    for item in items:
        match = _SINGLE_LETTER_PARENT_RE.match(normalize_question_number(item.get("number", "")))
        if match:
            groups[match.group(1)].append(item)
        else:
            others.append(item)

    warnings: list[str] = []
    result: list[dict] = list(others)

    for parent, entries in groups.items():
        entries.sort(key=lambda e: normalize_question_number(e.get("number", "")))
        letters = [
            _SINGLE_LETTER_PARENT_RE.match(normalize_question_number(e["number"])).group(2)
            for e in entries
        ]
        expected_letters = [chr(ord("a") + i) for i in range(len(entries))]
        texts = [e.get("text", "") for e in entries]

        if len(entries) >= 2 and letters == expected_letters and _looks_like_mcq_options(texts):
            word_lists = [t.split() for t in texts]
            prefix_len = _shared_word_prefix_len(word_lists)
            stem = " ".join(word_lists[0][:prefix_len]).strip(" :-")
            options = [
                f"({letter}) {' '.join(words[prefix_len:]).strip(' .,;:')}"
                for letter, words in zip(letters, word_lists)
            ]
            base = entries[0]
            result.append({
                **base,
                "number": parent,
                "text": f"{stem}: " + " ".join(options),
                "marks": next((e.get("marks") for e in entries if e.get("marks") is not None), None),
            })
            warnings.append(
                f"Question '{parent}' was split into {len(entries)} lettered items that were "
                "actually multiple-choice options, not separate sub-parts; merged back into one question."
            )
        else:
            result.extend(entries)

    return result, warnings


def run(pages: list[PageImage], file_path: str | None = None) -> QuestionExtractionResult:
    raw_items, extraction_warnings = _extract_raw_items(pages)
    expanded_items = [part for item in raw_items for part in _split_bundled_subparts(item)]
    deduped_items, dedupe_warnings = _dedupe_across_chunks(expanded_items)
    merged_items, mcq_warnings = _merge_mcq_option_siblings(deduped_items)
    warnings: list[str] = extraction_warnings + dedupe_warnings + mcq_warnings

    questions: list[Question] = []

    for item in merged_items:
        bbox = None
        raw_bbox = item.get("bounding_box")
        if file_path and item.get("text"):
            refined = refine_text_region(file_path, item.get("page", 0), item["text"])
            if refined:
                raw_bbox = refined
        if raw_bbox:
            try:
                bbox = QuestionBoundingBox(**raw_bbox)
            except ValidationError as exc:
                warnings.append(
                    f"Discarded invalid bounding box for question {item.get('number')}: {exc}"
                )

        try:
            question = Question(
                number=item["number"],
                normalized_number=normalize_question_number(item["number"]),
                text=item["text"],
                marks=item.get("marks"),
                page=item["page"],
                order=0,  # placeholder - real order is assigned deterministically below
                bounding_box=bbox,
            )
        except (ValidationError, KeyError) as exc:
            warnings.append(f"Skipped malformed question entry: {exc}")
            continue

        questions.append(question)

    # Never trust the model's own item order - it's especially unreliable
    # once results from multiple chunks are concatenated. Sort deterministically
    # by (main number, sub-part letters) and only fall back to page/appearance
    # order for anything that couldn't be parsed as a number at all.
    questions.sort(key=lambda q: (extract_order_key(q.normalized_number), q.page))
    for order, question in enumerate(questions, start=1):
        question.order = order

    return QuestionExtractionResult(
        questions=questions, page_count=len(pages), warnings=warnings
    )
