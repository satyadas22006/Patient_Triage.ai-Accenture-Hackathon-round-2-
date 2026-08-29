"""
engine/nlp_classifier.py

Owner: Qudsia — Day 1

Baseline implementation is complete. Primary path uses the transformers
zero-shot-classification pipeline (facebook/bart-large-mnli). If the model
can't be loaded (no internet on first run, offline demo environment, etc.)
this falls back to a keyword-based heuristic instead of crashing — the same
"degrade safely, don't fail silently" principle the rest of the product is
built on.

Qudsia: the fallback keyword lists are intentionally short — expand them,
or replace the whole fallback, as you see fit. Just keep the return
contract (label in LABELS, confidence in [0.0, 1.0]).
"""

from __future__ import annotations

import re
from functools import lru_cache

LABELS = ["Cardiac", "Respiratory", "Trauma", "Routine"]

# Rough per-label urgency weight — used to turn (label, confidence) into a
# single 0-1 urgency score. Routine pulls the score down even at high
# confidence; the other three pull it up.
LABEL_URGENCY_WEIGHT = {
    "Cardiac": 1.0,
    "Respiratory": 0.9,
    "Trauma": 0.95,
    "Routine": 0.05,
}

# Weighted keywords — some phrases are much stronger red flags than others
# ("crushing", "radiating" are classic cardiac-emergency descriptors and
# should move the needle a lot more than a bare mention of "chest").
_FALLBACK_KEYWORDS = {
    "Cardiac": {
        "chest": 0.30, "heart": 0.30, "palpitation": 0.40, "tight": 0.35,
        "pressure": 0.35, "crushing": 0.50, "radiating": 0.45, "left arm": 0.40,
    },
    "Respiratory": {
        "breath": 0.35, "breathing": 0.30, "wheeze": 0.40, "cough": 0.25,
        "choking": 0.50, "oxygen": 0.30, "shortness": 0.45, "gasping": 0.45,
    },
    "Trauma": {
        "bleeding": 0.40, "fracture": 0.45, "fell": 0.30, "accident": 0.30,
        "wound": 0.35, "broken": 0.40, "crash": 0.40, "laceration": 0.40,
    },
}


# --------------------------------------------------------------------------- #
# Model loading (cached — only load once per process)
# --------------------------------------------------------------------------- #

@lru_cache(maxsize=1)
def _get_pipeline():
    """
    Lazily load the zero-shot classification pipeline. Cached with
    lru_cache so it only loads once per process (in Streamlit, wrap the
    call site with @st.cache_resource as well — see ui/app.py).

    Raises whatever transformers/torch raises on failure; callers must
    catch this and fall back.
    """
    from transformers import pipeline  # imported lazily so a missing/slow
    return pipeline("zero-shot-classification", model="facebook/bart-large-mnli")


def _classify_with_model(chief_complaint: str) -> tuple[str, float]:
    clf = _get_pipeline()
    result = clf(chief_complaint, candidate_labels=LABELS)
    return result["labels"][0], float(result["scores"][0])


def _classify_with_fallback(chief_complaint: str) -> tuple[str, float]:
    """
    Simple keyword-overlap heuristic used only if the transformer model
    can't be loaded. Not a substitute for the real classifier — just a
    safety net so a demo never hard-crashes on a missing model download.
    """
    text = chief_complaint.lower()
    scores = {}
    for label, keywords in _FALLBACK_KEYWORDS.items():
        hits = sum(1 for kw in keywords if re.search(rf"\b{re.escape(kw)}", text))
        scores[label] = hits

    best_label = max(scores, key=scores.get)
    if scores[best_label] == 0:
        return "Routine", 0.6
    confidence = min(0.95, 0.5 + 0.15 * scores[best_label])
    return best_label, confidence


# --------------------------------------------------------------------------- #
# Public functions
# --------------------------------------------------------------------------- #

def classify_chief_complaint(chief_complaint: str) -> tuple[str, float, bool]:
    """
    Classify a chief complaint.

    Returns:
        (label, confidence, used_fallback) — label is one of LABELS,
        confidence is in [0.0, 1.0], used_fallback is True if the
        keyword heuristic was used instead of the real model (the UI
        should surface this to the user, not hide it).
    """
    try:
        label, confidence = _classify_with_model(chief_complaint)
        return label, confidence, False
    except Exception:
        label, confidence = _classify_with_fallback(chief_complaint)
        return label, confidence, True


def score_nlp_urgency(chief_complaint: str) -> float:
    """
    Score how urgent a patient's chief complaint sounds.

    Returns:
        Float in [0.0, 1.0] — higher means more urgent.
    """
    label, confidence, _ = classify_chief_complaint(chief_complaint)
    weight = LABEL_URGENCY_WEIGHT[label]
    return round(confidence * weight, 4)


def get_nlp_label(chief_complaint: str) -> str:
    """Convenience accessor for just the top predicted label."""
    label, _, _ = classify_chief_complaint(chief_complaint)
    return label
