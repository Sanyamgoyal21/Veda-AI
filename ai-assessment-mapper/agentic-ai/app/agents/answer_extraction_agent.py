"""Extracts every handwritten answer (with exact page regions) from a
student's answer sheet document."""
from collections import defaultdict

from pydantic import ValidationError

from app.prompts import answer_prompt
from app.schemas.answer_schema import Answer, AnswerExtractionResult, AnswerRegion
from app.services import vision_service
from app.services.chunking import chunk_pages
from app.services.pdf_service import PageImage, refine_text_region
from app.utils.normalization import normalize_question_number

# A region covering more than this fraction of the page is treated as a
# probably-imprecise "whole block" guess rather than a tight answer region.
OVERSIZED_REGION_AREA = 0.9


def _extract_raw_items(pages: list[PageImage]) -> tuple[list[dict], list[str]]:
    """Runs extraction chunk-by-chunk (a single chunk for short documents)."""
    chunks = chunk_pages(pages)
    items: list[dict] = []
    warnings: list[str] = []

    for chunk_index, chunk in enumerate(chunks):
        raw = vision_service.run_structured_extraction(
            system_prompt=answer_prompt.SYSTEM_PROMPT,
            user_prompt=answer_prompt.build_user_prompt(len(chunk.pages)),
            pages=chunk.pages,
            tool_name=answer_prompt.TOOL_NAME,
            tool_description=answer_prompt.TOOL_DESCRIPTION,
            input_schema=answer_prompt.INPUT_SCHEMA,
        )
        warnings.extend(raw.get("warnings", []))
        for item in raw.get("answers", []):
            items.append({**item, "_chunk_index": chunk_index})

    return items, warnings


def _regions_overlap(a: dict, b: dict, min_iou: float = 0.4) -> bool:
    if a.get("page") != b.get("page"):
        return False
    ax0, ay0, aw, ah = a["x"], a["y"], a["width"], a["height"]
    bx0, by0, bw, bh = b["x"], b["y"], b["width"], b["height"]
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax0 + aw, bx0 + bw), min(ay0 + ah, by0 + bh)
    if ix1 <= ix0 or iy1 <= iy0:
        return False
    intersection = (ix1 - ix0) * (iy1 - iy0)
    union = aw * ah + bw * bh - intersection
    return union > 0 and intersection / union >= min_iou


def _merge_answer_group(entries: list[dict]) -> dict:
    """
    Multiple chunks can independently detect the same answer (an overlap-page
    duplicate) or each detect a different, incomplete slice of one answer
    that genuinely spans a chunk boundary. Either way, the fix is the same:
    take the union of every region seen (deduping near-identical ones on the
    same page), and concatenate text that isn't already a near-duplicate/
    substring of text already included. This never silently drops content -
    worst case on a pathological multi-page-spanning answer is some
    redundant repeated text, not a missing region.
    """
    entries_by_first_page = sorted(
        entries, key=lambda e: min((r.get("page", 0) for r in e.get("regions", [])), default=0)
    )

    merged_regions: list[dict] = []
    for entry in entries_by_first_page:
        for region in entry.get("regions", []):
            if not any(_regions_overlap(region, existing) for existing in merged_regions):
                merged_regions.append(region)
    merged_regions.sort(key=lambda r: r.get("page", 0))

    texts: list[str] = []
    for entry in entries_by_first_page:
        text = (entry.get("text") or "").strip()
        if text and not any(text in seen or seen in text for seen in texts):
            texts.append(text)

    base = entries_by_first_page[0]
    return {
        **base,
        "regions": merged_regions,
        "text": " ".join(texts),
        "confidence": min((e.get("confidence", 0.5) for e in entries), default=0.5),
    }


def _dedupe_and_merge_answers(items: list[dict]) -> tuple[list[dict], list[str]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        key = normalize_question_number(item.get("detected_question_number", ""))
        groups[key].append(item)

    merged: list[dict] = []
    warnings: list[str] = []
    for key, entries in groups.items():
        if len(entries) == 1 or not key:
            merged.extend(entries)
            continue

        # A repeated number is not by itself a duplicate. OCR can misread a
        # distant answer as (say) 28(iii), while the real 28(iii) also exists.
        # Merge only entries emitted by different chunks that share a page;
        # that shared page is the evidence that this is overlap/continuation.
        pending = list(entries)
        while pending:
            component = [pending.pop(0)]
            changed = True
            while changed:
                changed = False
                component_chunks = {e.get("_chunk_index") for e in component}
                for candidate in pending[:]:
                    candidate_chunk = candidate.get("_chunk_index")
                    different_chunk = (
                        candidate_chunk not in component_chunks
                        or (candidate_chunk is None and component_chunks == {None})
                    )
                    regions_overlap = any(
                        _regions_overlap(a, b)
                        for entry in component
                        for a in entry.get("regions", [])
                        for b in candidate.get("regions", [])
                    )
                    if different_chunk and regions_overlap:
                        component.append(candidate)
                        pending.remove(candidate)
                        changed = True

            if len(component) == 1:
                merged.extend(component)
            else:
                result = _merge_answer_group(component)
                merged.append(result)
                warnings.append(
                    f"Answer '{result.get('detected_question_number')}' was independently detected "
                    f"in {len(component)} overlapping chunks; merged into one answer covering "
                    f"{len(result['regions'])} region(s)."
                )
    return merged, warnings


def run(pages: list[PageImage], file_path: str | None = None) -> AnswerExtractionResult:
    raw_items, extraction_warnings = _extract_raw_items(pages)
    merged_items, merge_warnings = _dedupe_and_merge_answers(raw_items)
    warnings: list[str] = extraction_warnings + merge_warnings

    answers: list[Answer] = []

    for item in merged_items:
        regions: list[AnswerRegion] = []
        for raw_region in item.get("regions", []):
            # Vision models guess pixel coordinates unreliably. When the
            # source is a typed PDF (not a photographed scan), replace the
            # guess with an exact bounding box found via real text search.
            if file_path:
                refined = refine_text_region(file_path, raw_region.get("page", 0), item.get("text", ""))
                if refined:
                    raw_region = refined

            try:
                region = AnswerRegion(**raw_region)
            except ValidationError as exc:
                warnings.append(
                    f"Discarded invalid region for answer "
                    f"{item.get('detected_question_number')}: {exc}"
                )
                continue

            if region.area > OVERSIZED_REGION_AREA:
                warnings.append(
                    f"Answer '{item.get('detected_question_number')}' has a region covering "
                    f"{region.area:.0%} of the page - likely an imprecise whole-block guess"
                )

            regions.append(region)

        if not regions:
            warnings.append(
                f"Answer {item.get('detected_question_number')} had no valid "
                "regions and was dropped"
            )
            continue

        try:
            answer = Answer(
                detected_question_number=item["detected_question_number"],
                normalized_question_number=normalize_question_number(
                    item["detected_question_number"]
                ),
                text=item["text"],
                confidence=item.get("confidence", 0.5),
                regions=regions,
            )
        except (ValidationError, KeyError) as exc:
            warnings.append(f"Skipped malformed answer entry: {exc}")
            continue

        answers.append(answer)

    return AnswerExtractionResult(answers=answers, page_count=len(pages), warnings=warnings)
