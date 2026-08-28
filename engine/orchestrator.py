"""
engine/orchestrator.py

Owner: Satya — Day 2

The single entry point the UI calls. Everything about *which* pipeline a
patient goes through, and how errors are handled, lives here — the UI
layer should never call nlp_classifier / risk_engine / vitals_age /
mass_casualty directly.
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.mass_casualty import triage_single_mass_casualty
from engine.nlp_classifier import classify_chief_complaint
from engine.risk_engine import DEFAULT_ALPHA, DEFAULT_BETA, DEFAULT_GAMMA, check_decide_triggers, compute_risk, map_risk_to_esi
from engine.vitals_age import score_age_factor, score_vital_deviation
from models.schemas import PatientInput, TriageResult


class TriageError(Exception):
    """Raised when the pipeline cannot produce a result at all."""


# If any decide-trigger fires, the recommended ESI level is never allowed to
# be weaker (numerically higher) than this. 2 = "Emergent" — see the ESI
# scale in risk_engine.py.
DECIDE_TRIGGER_ESI_CEILING = 2


@dataclass
class TriageRunMeta:
    """Extra, UI-relevant metadata about how a result was produced."""

    used_nlp_fallback: bool = False


def run_triage(
    patient: PatientInput,
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
    gamma: float = DEFAULT_GAMMA,
) -> tuple[TriageResult, TriageRunMeta]:
    """
    Route a PatientInput to the correct pipeline and return a TriageResult.

    - mass_casualty_mode=True  -> deterministic, vitals-only bypass queue.
    - mass_casualty_mode=False -> full MMTG pipeline (NLP + vitals + age).

    Raises:
        TriageError if neither pipeline can produce a result (e.g. a
        completely unexpected internal failure). Both individual pipelines
        already degrade gracefully on their own (see nlp_classifier.py's
        fallback), so this should be rare — it exists as a last line of
        defense so the UI never sees a raw traceback.
    """
    try:
        if patient.mass_casualty_mode:
            result = triage_single_mass_casualty(patient)
            return result, TriageRunMeta(used_nlp_fallback=False)

        nlp_label, nlp_confidence, used_fallback = classify_chief_complaint(
            patient.chief_complaint
        )
        from engine.nlp_classifier import LABEL_URGENCY_WEIGHT

        nlp_urgency = round(nlp_confidence * LABEL_URGENCY_WEIGHT[nlp_label], 4)

        vital_dev = score_vital_deviation(
            patient.age, patient.heart_rate, patient.spo2, patient.temperature
        )
        age_factor = score_age_factor(patient.age)

        risk_score, breakdown = compute_risk(
            vital_dev, nlp_urgency, age_factor, alpha=alpha, beta=beta, gamma=gamma
        )
        esi_level = map_risk_to_esi(risk_score)
        decisions = check_decide_triggers(vital_dev, nlp_urgency, nlp_label, patient.heart_rate)

        # Coherence invariant: if the system is confident enough to auto-trigger
        # a protocol action (e.g. auto-order an ECG), it can never simultaneously
        # recommend an ESI level weaker than "Emergent". A decide-trigger and a
        # low-urgency recommendation contradicting each other is exactly the kind
        # of inconsistency that erodes clinician trust — so we enforce it as an
        # explicit floor here rather than relying on threshold tuning alone.
        if decisions and esi_level > DECIDE_TRIGGER_ESI_CEILING:
            esi_level = DECIDE_TRIGGER_ESI_CEILING

        result = TriageResult(
            risk_score=risk_score,
            esi_level=esi_level,
            decisions=decisions,
            mass_casualty_mode=False,
            explain=breakdown,
            reason=None,
        )
        return result, TriageRunMeta(used_nlp_fallback=used_fallback)

    except Exception as exc:  # last line of defense — UI must never see a raw traceback
        raise TriageError(f"Triage pipeline failed to produce a result: {exc}") from exc
