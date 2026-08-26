"""Confidence thresholds and helpers shared across agents."""

EXACT_SCORE = 1.0
NORMALIZED_SCORE = 0.9
FUZZY_MIN_SCORE = 0.6
SEMANTIC_MIN_SCORE = 0.45
LOW_CONFIDENCE_THRESHOLD = 0.6


def is_low_confidence(score: float) -> bool:
    return score < LOW_CONFIDENCE_THRESHOLD


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))
