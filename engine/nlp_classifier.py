"""
engine/nlp_classifier.py

Zero-shot NLP urgency classifier with a deterministic safety layer.

Pipeline:
    1. High-signal clinical phrase detection
    2. Transformer zero-shot classification
    3. Keyword fallback if the transformer is unavailable

The safety layer exists because a zero-shot model can occasionally assign
a moderate confidence to the wrong category even when the complaint contains
a highly characteristic emergency pattern.

The application remains AI-assisted:
- Transformer NLP is still used for general complaints.
- Deterministic safety rules only override clearly high-signal patterns.
"""

from __future__ import annotations

import re
from functools import lru_cache


# ============================================================================
# LABELS
# ============================================================================

LABELS = [
    "Cardiac",
    "Respiratory",
    "Trauma",
    "Routine",
]


# ============================================================================
# NLP URGENCY WEIGHTS
# ============================================================================

LABEL_URGENCY_WEIGHT = {
    "Cardiac": 1.0,
    "Respiratory": 0.9,
    "Trauma": 0.95,
    "Routine": 0.05,
}


# ============================================================================
# KEYWORD FALLBACK
# ============================================================================

_FALLBACK_KEYWORDS = {
    "Cardiac": {
        "chest": 0.30,
        "heart": 0.30,
        "palpitation": 0.40,
        "tight": 0.35,
        "pressure": 0.35,
        "crushing": 0.50,
        "radiating": 0.45,
        "left arm": 0.40,
        "shortness of breath": 0.40,
        "syncope": 0.45,
    },
    "Respiratory": {
        "breath": 0.35,
        "breathing": 0.30,
        "wheeze": 0.40,
        "cough": 0.25,
        "choking": 0.50,
        "oxygen": 0.30,
        "shortness": 0.45,
        "gasping": 0.45,
        "stridor": 0.50,
        "throat": 0.20,
    },
    "Trauma": {
        "bleeding": 0.40,
        "fracture": 0.45,
        "fell": 0.30,
        "accident": 0.30,
        "wound": 0.35,
        "broken": 0.40,
        "crash": 0.40,
        "laceration": 0.40,
        "stab": 0.55,
        "crush": 0.50,
    },
}


# ============================================================================
# HIGH-SIGNAL SAFETY PATTERNS
# ============================================================================

# These are deliberately narrow.
# They are NOT generic "chest pain = cardiac" rules.
# They look for combinations of strongly characteristic language.

_CARDIAC_STRONG_PATTERNS = [
    (
        "chest",
        "crushing",
    ),
    (
        "chest",
        "radiating",
    ),
    (
        "chest",
        "left arm",
    ),
    (
        "chest",
        "pressure",
    ),
    (
        "chest",
        "tight",
    ),
    (
        "left arm",
        "radiating",
    ),
]

_RESPIRATORY_STRONG_PATTERNS = [
    (
        "can't catch my breath",
    ),
    (
        "cannot catch my breath",
    ),
    (
        "gasping",
    ),
    (
        "choking",
    ),
    (
        "stridor",
    ),
    (
        "severe wheezing",
    ),
    (
        "severe shortness of breath",
    ),
]

_TRAUMA_STRONG_PATTERNS = [
    (
        "heavy bleeding",
    ),
    (
        "severe bleeding",
    ),
    (
        "badly broken",
    ),
    (
        "open fracture",
    ),
    (
        "major trauma",
    ),
]


# ============================================================================
# MODEL
# ============================================================================

@lru_cache(maxsize=1)
def _get_pipeline():
    """
    Lazily load the zero-shot transformer pipeline.

    The pipeline is cached so the model is loaded only once per process.
    """

    from transformers import pipeline

    return pipeline(
        "zero-shot-classification",
        model="facebook/bart-large-mnli",
    )


def _classify_with_model(
    chief_complaint: str,
) -> tuple[str, float]:
    """Run transformer-based zero-shot classification."""

    clf = _get_pipeline()

    result = clf(
        chief_complaint,
        candidate_labels=LABELS,
    )

    return (
        result["labels"][0],
        float(result["scores"][0]),
    )


# ============================================================================
# KEYWORD FALLBACK
# ============================================================================

def _classify_with_fallback(
    chief_complaint: str,
) -> tuple[str, float]:
    """
    Keyword-based fallback used when transformer inference fails.
    """

    text = chief_complaint.lower()

    scores: dict[str, float] = {
        "Cardiac": 0.0,
        "Respiratory": 0.0,
        "Trauma": 0.0,
    }

    for label, keywords in _FALLBACK_KEYWORDS.items():

        for keyword, weight in keywords.items():

            if re.search(
                rf"\b{re.escape(keyword)}",
                text,
            ):
                scores[label] += weight

    best_label = max(
        scores,
        key=scores.get,
    )

    best_score = scores[best_label]

    if best_score == 0:
        return "Routine", 0.6

    confidence = min(
        0.95,
        0.5 + (best_score * 0.25),
    )

    return (
        best_label,
        confidence,
    )


# ============================================================================
# SAFETY CLASSIFICATION
# ============================================================================

def _contains_pattern(
    text: str,
    pattern: tuple[str, ...],
) -> bool:
    """
    Return True if every phrase in the pattern is present.
    """

    return all(
        phrase in text
        for phrase in pattern
    )


def _classify_with_safety_rules(
    chief_complaint: str,
) -> tuple[str | None, float]:
    """
    Detect narrow, high-signal emergency language.

    Returns:
        (label, confidence)

    Returns:
        (None, 0.0) when no high-signal pattern is detected.
    """

    text = " ".join(
        chief_complaint.lower().split()
    )

    # ------------------------------------------------------------------------
    # CARDIAC
    # ------------------------------------------------------------------------

    for pattern in _CARDIAC_STRONG_PATTERNS:

        if _contains_pattern(text, pattern):

            return (
                "Cardiac",
                0.95,
            )

    # ------------------------------------------------------------------------
    # RESPIRATORY
    # ------------------------------------------------------------------------

    for pattern in _RESPIRATORY_STRONG_PATTERNS:

        if _contains_pattern(text, pattern):

            return (
                "Respiratory",
                0.95,
            )

    # ------------------------------------------------------------------------
    # TRAUMA
    # ------------------------------------------------------------------------

    for pattern in _TRAUMA_STRONG_PATTERNS:

        if _contains_pattern(text, pattern):

            return (
                "Trauma",
                0.95,
            )

    return (
        None,
        0.0,
    )


# ============================================================================
# PUBLIC CLASSIFIER
# ============================================================================

def classify_chief_complaint(
    chief_complaint: str,
) -> tuple[str, float, bool]:
    """
    Classify a chief complaint.

    Order:
        1. High-signal safety override
        2. Transformer model
        3. Keyword fallback

    Returns:
        (label, confidence, used_fallback)
    """

    text = (chief_complaint or "").strip()

    # Empty input should still be handled gracefully.
    if not text:
        return (
            "Routine",
            0.6,
            True,
        )

    # ------------------------------------------------------------------------
    # 1. HIGH-SIGNAL SAFETY OVERRIDE
    # ------------------------------------------------------------------------

    safety_label, safety_confidence = (
        _classify_with_safety_rules(text)
    )

    if safety_label is not None:

        # This is not a model failure, so keep used_fallback=False.
        return (
            safety_label,
            safety_confidence,
            False,
        )

    # ------------------------------------------------------------------------
    # 2. TRANSFORMER MODEL
    # ------------------------------------------------------------------------

    try:

        label, confidence = _classify_with_model(
            text
        )

        return (
            label,
            confidence,
            False,
        )

    except Exception:

        # --------------------------------------------------------------------
        # 3. KEYWORD FALLBACK
        # --------------------------------------------------------------------

        label, confidence = _classify_with_fallback(
            text
        )

        return (
            label,
            confidence,
            True,
        )


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def score_nlp_urgency(
    chief_complaint: str,
) -> float:
    """
    Convert classification into a single urgency score in [0, 1].
    """

    label, confidence, _ = classify_chief_complaint(
        chief_complaint
    )

    weight = LABEL_URGENCY_WEIGHT[label]

    return round(
        confidence * weight,
        4,
    )


def get_nlp_label(
    chief_complaint: str,
) -> str:
    """Return only the predicted label."""

    label, _, _ = classify_chief_complaint(
        chief_complaint
    )

    return label


def get_classification_confidence(
    chief_complaint: str,
) -> float:
    """Return only the classification confidence."""

    _, confidence, _ = classify_chief_complaint(
        chief_complaint
    )

    return confidence


def classify_with_metadata(
    chief_complaint: str,
) -> dict:
    """
    Return full classification metadata.
    """

    label, confidence, used_fallback = (
        classify_chief_complaint(
            chief_complaint
        )
    )

    weight = LABEL_URGENCY_WEIGHT[label]

    urgency_score = round(
        confidence * weight,
        4,
    )

    return {
        "label": label,
        "confidence": round(
            confidence,
            4,
        ),
        "urgency_score": urgency_score,
        "used_fallback": used_fallback,
    }
    