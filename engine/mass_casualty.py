"""
engine/mass_casualty.py

Owner: Ayush — Day 2

Baseline implementation is complete and tested. This path NEVER calls the
NLP model — that's the whole point (speed and reliability during a surge).
It reuses the vitals/age scoring from vitals_age.py and risk_engine.py's
ESI mapping, but composes them completely independently of the normal
pipeline, so a bug or slowdown in the NLP path can never affect this one.
"""

from __future__ import annotations

from engine.risk_engine import map_risk_to_esi
from engine.vitals_age import score_age_factor, score_vital_deviation
from models.schemas import ExplainabilityBreakdown, PatientInput, TriageResult

# Vitals-only weighting — no beta term, since NLP is bypassed entirely.
# Vitals dominate; age is a secondary modifier.
MCM_VITAL_WEIGHT = 0.75
MCM_AGE_WEIGHT = 0.25


def _reason_for(vital_deviation: float, age_factor: float, heart_rate: int, spo2: float) -> str:
    """Build a short, plain-English reason for this patient's rank."""
    reasons = []
    if spo2 < 90:
        reasons.append("SpO2 critically low")
    elif spo2 < 95:
        reasons.append("SpO2 below normal")
    if heart_rate > 130 or heart_rate < 50:
        reasons.append("heart rate significantly abnormal")
    if age_factor >= 0.5:
        reasons.append("high-risk age group")
    if not reasons:
        reasons.append("vitals within or near normal range")
    return ", ".join(reasons).capitalize()


def mass_casualty_queue(patients: list[PatientInput]) -> list[TriageResult]:
    """
    Rank a batch of patients using ONLY their vitals (no NLP call at all).

    Args:
        patients: a batch of PatientInput.

    Returns:
        TriageResult objects, ordered most to least urgent (index 0 = seen
        first), each with mass_casualty_mode=True, explain=None (this path
        is rule-based, not weighted — nothing to attribute to alpha/beta/
        gamma), and a one-line `reason`.
    """
    scored: list[tuple[float, PatientInput, float, float]] = []

    for p in patients:
        vital_dev = score_vital_deviation(p.age, p.heart_rate, p.spo2, p.temperature)
        age_factor = score_age_factor(p.age)
        risk = round(min(1.0, MCM_VITAL_WEIGHT * vital_dev + MCM_AGE_WEIGHT * age_factor), 4)
        scored.append((risk, p, vital_dev, age_factor))

    scored.sort(key=lambda row: row[0], reverse=True)  # highest risk first

    results: list[TriageResult] = []
    for risk, p, vital_dev, age_factor in scored:
        results.append(
            TriageResult(
                risk_score=risk,
                esi_level=map_risk_to_esi(risk),
                decisions=[],
                mass_casualty_mode=True,
                explain=None,
                reason=_reason_for(vital_dev, age_factor, p.heart_rate, p.spo2),
            )
        )
    return results


def triage_single_mass_casualty(patient: PatientInput) -> TriageResult:
    """Convenience wrapper for the common single-patient UI case."""
    return mass_casualty_queue([patient])[0]
