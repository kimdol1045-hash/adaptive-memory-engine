from __future__ import annotations


def passes_confidence(confidence: float, threshold: float = 0.7) -> bool:
    return confidence >= threshold
