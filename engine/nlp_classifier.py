"""
engine/nlp_classifier.py — Production Implementation

Zero-shot NLP urgency classifier with keyword fallback.
- Loads facebook/bart-large-mnli once and caches it (lru_cache + @st.cache_resource in UI).
- Falls back to keyword heuristics if model load fails (e.g. offline environment).
- Returns label, confidence, and fallback indicator so UI can warn users.
- Urgency weights tuned so cardinal symptoms (cardiac: "crushing", respiratory:
  "choking") move the needle more than symptom mentions alone.
"""

from __future__ import annotations

import re
from functools import lru_cache

LABELS = ["Cardiac", "Respiratory", "Trauma", "Routine"]

# Per-label urgency weight — turns (label, confidence) into a single urgency score.
# Routine pulls down; Cardiac/Respiratory/Trauma push up.
LABEL_URGENCY_WEIGHT = {
    "Cardiac": 1.0,
    "Respiratory": 0.9,
    "Trauma": 0.95,
    "Routine": 0.05,
}

# Weighted keyword fallback — strong phrases move the needle more.
# "crushing" (cardiac) > "chest" (cardiac mention).
# "choking" (respiratory emergency) > "cough" (respiratory mention).
_FALLBACK_KEYWORDS = {
    "Cardiac": {
        "chest": 0.30, "heart": 0.30, "palpitation": 0.40, "tight": 0.35,
        "pressure": 0.35, "crushing": 0.50, "radiating": 0.45, "left arm": 0.40,
        "shortness of breath": 0.40, "syncope": 0.45,
    },
    "Respiratory": {
        "breath": 0.35, "breathing": 0.30, "wheeze": 0.40, "cough": 0.25,
        "choking": 0.50, "oxygen": 0.30, "shortness": 0.45, "gasping": 0.45,
        "stridor": 0.50, "throat": 0.20,
    },
    "Trauma": {
        "bleeding": 0.40, "fracture": 0.45, "fell": 0.30, "accident": 0.30,
        "wound": 0.35, "broken": 0.40, "crash": 0.40, "laceration": 0.40,
        "stab": 0.55, "crush": 0.50,
    },
}


@lru_cache(maxsize=1)
def _get_pipeline():
    """Lazily load the zero-shot classification pipeline (cached via lru_cache)."""
    from transformers import pipeline
    return pipeline("zero-shot-classification", model="facebook/bart-large-mnli")


def _classify_with_model(chief_complaint: str) -> tuple[str, float]:
    """Call the real zero-shot model."""
    clf = _get_pipeline()
    result = clf(chief_complaint, candidate_labels=LABELS)
    return result["labels"][0], float(result["scores"][0])


def _classify_with_fallback(chief_complaint: str) -> tuple[str, float]:
    """Keyword-based fallback used if the transformer model can't load."""
    text = chief_complaint.lower()
    scores = {}

    for label, keywords in _FALLBACK_KEYWORDS.items():
        weight_sum = 0.0
        for kw, weight in keywords.items():
            if re.search(rf"\b{re.escape(kw)}", text):
                weight_sum += weight
        scores[label] = weight_sum

    best_label = max(scores, key=scores.get)
    if scores[best_label] == 0:
        return "Routine", 0.6

    confidence = min(0.95, 0.5 + (scores[best_label] * 0.25))
    return best_label, confidence


def classify_chief_complaint(chief_complaint: str) -> tuple[str, float, bool]:
    """
    Classify a chief complaint into one of four urgency categories.

    Returns:
        (label, confidence, used_fallback)
    """
    try:
        label, confidence = _classify_with_model(chief_complaint)
        return label, confidence, False
    except Exception:
        label, confidence = _classify_with_fallback(chief_complaint)
        return label, confidence, True


def score_nlp_urgency(chief_complaint: str) -> float:
    """Score how urgent a patient's chief complaint sounds (0.0–1.0)."""
    label, confidence, _ = classify_chief_complaint(chief_complaint)
    weight = LABEL_URGENCY_WEIGHT[label]
    return round(confidence * weight, 4)


def get_nlp_label(chief_complaint: str) -> str:
    """Convenience accessor for just the top predicted label."""
    label, _, _ = classify_chief_complaint(chief_complaint)
    return label


def get_classification_confidence(chief_complaint: str) -> float:
    """Convenience accessor for just the confidence score."""
    _, confidence, _ = classify_chief_complaint(chief_complaint)
    return confidence


def classify_with_metadata(chief_complaint: str) -> dict:
    """Full classification metadata — useful for debugging or UI tooltips."""
    label, confidence, used_fallback = classify_chief_complaint(chief_complaint)
    weight = LABEL_URGENCY_WEIGHT[label]
    urgency_score = round(confidence * weight, 4)

    return {
        "label": label,
        "confidence": round(confidence, 4),
        "urgency_score": urgency_score,
        "used_fallback": used_fallback,
    }
