"""Deterministic segment validation, continuation scoring and answer grouping."""
import logging
from collections import defaultdict

from app.schemas.answer_schema import Answer, AnswerRegion, AnswerSegment
from app.services.pdf_service import refine_text_region
from app.utils.normalization import normalize_question_number

logger = logging.getLogger(__name__)


def _continuation_score(segment: AnswerSegment, has_active: bool) -> float:
    """Evidence-weighted score; each term has a concrete observable meaning."""
    if not has_active:
        return 0.0
    score = 0.45  # no validated new marker
    if segment.continuation_likely:
        score += 0.20
    score += 0.20 * segment.continuation_confidence
    if segment.segment_type in {"CONTINUATION", "TEXT_FRAGMENT", "DIAGRAM_LABEL", "MATHEMATICAL_LABEL"}:
        score += 0.15
    if segment.has_diagram:
        score += 0.05
    return min(1.0, score)


def group_segments(
    segments: list[AnswerSegment], valid_numbers: set[str], file_path: str | None = None
) -> tuple[list[Answer], list[str]]:
    """
    Group content only after marker validation against the question paper.

    `file_path`: when set and the source is a typed PDF (not a photographed
    scan), each part's AI-guessed region is replaced with an exact bounding
    box found via real text search - vision models guess pixel coordinates
    unreliably, especially with several similarly-worded answers on one page.
    """
    ordered = sorted(segments, key=lambda s: (s.original_page, s.visual_order, s.bbox.y))
    unique: list[AnswerSegment] = []
    for segment in ordered:
        duplicate = any(
            segment.original_page == old.original_page
            and _iou(segment.bbox, old.bbox) >= 0.4
            and (segment.text.strip() in old.text.strip() or old.text.strip() in segment.text.strip())
            for old in unique
        )
        if not duplicate:
            unique.append(segment)
    ordered = unique
    grouped: dict[str, list[AnswerSegment]] = defaultdict(list)
    first_seen: list[str] = []
    active: str | None = None
    warnings: list[str] = []

    for segment in ordered:
        candidate = normalize_question_number(segment.detected_question_number or "")
        valid_start = (
            segment.segment_type in {"ANSWER_START", "SUBPART"}
            and candidate in valid_numbers
            # Handwritten but physically visible markers are often assigned
            # moderate OCR confidence. Classification + master-index +
            # content grounding carry more signal than a high numeric cutoff.
            and segment.question_number_confidence >= 0.40
        )
        if valid_start:
            active = candidate
            if active not in first_seen:
                first_seen.append(active)
            decision = "NEW_ANSWER"
            score = 0.0
        else:
            score = _continuation_score(segment, active is not None)
            if active is None:
                # Content before the first trustworthy marker is retained as
                # an extraction warning, never promoted to a fake Answer.
                warnings.append(
                    f"Ignored unanchored content on page {segment.original_page}; "
                    f"candidate '{segment.detected_question_number or 'none'}' was not a valid answer start"
                )
                logger.info("answer_segment", extra={"page": segment.original_page, "detected": candidate or None,
                            "continuation_score": score, "decision": "UNANCHORED_CONTENT"})
                continue
            decision = "CONTINUATION" if score >= 0.60 else "CONTENT"

        grouped[active].append(segment)
        logger.info("answer_segment", extra={"page": segment.original_page,
                    "detected": segment.detected_question_number, "previous_answer": active,
                    "continuation_score": round(score, 3), "decision": decision,
                    "grouped_into": active})

    answers: list[Answer] = []
    for number in first_seen:
        parts = grouped[number]
        regions: list[AnswerRegion] = []
        texts: list[str] = []
        for part in parts:
            region = part.bbox.model_copy(update={"page": part.original_page, "original_page": part.original_page})
            if file_path and part.text.strip():
                refined = refine_text_region(file_path, part.original_page, part.text)
                if refined:
                    refined_region = AnswerRegion(**{**refined, "original_page": part.original_page})
                    # A diagram can extend beyond the exact transcribed
                    # text - refine_text_region only ever bounds the TEXT it
                    # was given, so replacing the region outright would crop
                    # any accompanying diagram out of the highlighted area.
                    # Union with the AI's own original guess instead (it was
                    # told to span this answer's ENTIRE content, diagram
                    # included) so the precision gain never costs the
                    # diagram; text-only answers still get the tight box.
                    region = _union_regions(region, refined_region) if part.has_diagram else refined_region
            # Overlapping-window duplicates have the same page and near-
            # identical box - but IoU alone misses the case where one region
            # is almost entirely NESTED inside a much larger other one (e.g.
            # heights 0.8 and 0.3 from the same y-start: IoU lands at 0.375,
            # just under the old 0.4 cutoff, even though the smaller region
            # is 100% contained in the larger one). That's the exact shape
            # a fallback "whole block" guess and a second, tighter guess for
            # the same content tend to take, and left undeduped it renders
            # as confusing stacked/nested boxes for one answer. Merge into
            # the union instead of just dropping the new one, so overlap
            # never means losing content either.
            merged_into_existing = False
            for i, old in enumerate(regions):
                if _regions_overlap(region, old):
                    regions[i] = _union_regions(region, old)
                    merged_into_existing = True
                    break
            if not merged_into_existing:
                regions.append(region)
            text = part.text.strip()
            if text and not any(text in old or old in text for old in texts):
                texts.append(text)
        pages = sorted({r.page for r in regions})
        confidence = min((p.segment_confidence for p in parts), default=0.5)
        answers.append(Answer(id=f"answer-q{number}", detected_question_number=number,
                              normalized_question_number=number, text="\n\n".join(texts),
                              confidence=confidence, regions=regions, pages=pages,
                              has_diagram=any(p.has_diagram for p in parts)))
    return answers, warnings


def _iou(a: AnswerRegion, b: AnswerRegion) -> float:
    if a.page != b.page:
        return 0.0
    x0, y0 = max(a.x, b.x), max(a.y, b.y)
    x1, y1 = min(a.x + a.width, b.x + b.width), min(a.y + a.height, b.y + b.height)
    if x1 <= x0 or y1 <= y0:
        return 0.0
    intersection = (x1 - x0) * (y1 - y0)
    return intersection / (a.area + b.area - intersection)


def _regions_overlap(a: AnswerRegion, b: AnswerRegion) -> bool:
    """True for near-duplicate boxes (high IoU) OR when one region is
    almost entirely nested inside the other - IoU alone under-detects
    containment when the two boxes are very different sizes."""
    if a.page != b.page:
        return False
    x0, y0 = max(a.x, b.x), max(a.y, b.y)
    x1, y1 = min(a.x + a.width, b.x + b.width), min(a.y + a.height, b.y + b.height)
    if x1 <= x0 or y1 <= y0:
        return False
    intersection = (x1 - x0) * (y1 - y0)
    iou = intersection / (a.area + b.area - intersection)
    containment = intersection / min(a.area, b.area)
    return iou >= 0.4 or containment >= 0.7


def _union_regions(a: AnswerRegion, b: AnswerRegion) -> AnswerRegion:
    """Smallest region containing both inputs - used to keep a diagram that
    sits outside a precisely-matched text region from being cropped away."""
    x0, y0 = min(a.x, b.x), min(a.y, b.y)
    x1, y1 = max(a.x + a.width, b.x + b.width), max(a.y + a.height, b.y + b.height)
    return a.model_copy(update={"x": x0, "y": y0, "width": min(1.0 - x0, x1 - x0), "height": min(1.0 - y0, y1 - y0)})
