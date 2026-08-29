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


def run(pages: list[PageImage], file_path: str | None = None) -> QuestionExtractionResult:
    raw_items, extraction_warnings = _extract_raw_items(pages)
    expanded_items = [part for item in raw_items for part in _split_bundled_subparts(item)]
    deduped_items, dedupe_warnings = _dedupe_across_chunks(expanded_items)
    warnings: list[str] = extraction_warnings + dedupe_warnings

    questions: list[Question] = []

    for item in deduped_items:
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
