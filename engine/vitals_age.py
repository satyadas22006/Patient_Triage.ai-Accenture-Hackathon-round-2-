"""
engine/vitals_age.py

Owner: Ayush — Day 1

Baseline implementation is complete and tested. Ayush: feel free to refine
the clinical thresholds/weights below — the function signatures and return
contract (float in [0.0, 1.0]) must stay the same, since risk_engine.py and
orchestrator.py both depend on them.
"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# Clinical reference ranges (adult). Documented here so the scoring logic is
# auditable, not a black box — cite these if a judge asks.
# --------------------------------------------------------------------------- #

NORMAL_HR = (60, 100)          # bpm
NORMAL_SPO2_MIN = 95.0         # %
NORMAL_TEMP = (36.1, 37.2)     # deg C


def _deviation_fraction(value: float, low: float, high: float, hard_span: float) -> float:
    """
    How far `value` sits outside [low, high], normalized to [0.0, 1.0].

    0.0 if inside the normal range. Scales linearly up to 1.0 once the value
    is `hard_span` units past the boundary (clamped beyond that), so a mild
    deviation scores low and a severe one saturates at 1.0 instead of growing
    without bound.
    """
    if low <= value <= high:
        return 0.0
    distance = low - value if value < low else value - high
    return min(1.0, distance / hard_span)


def score_vital_deviation(age: int, heart_rate: int, spo2: float, temperature: float) -> float:
    """
    Score how far a patient's vitals deviate from safe clinical ranges.

    Combines three independent deviation fractions (heart rate, SpO2,
    temperature) into one score via a weighted max-and-average blend: the
    single worst vital dominates (a critically low SpO2 alone should already
    read as high-risk), but the other two still nudge the score up, so two
    moderately-abnormal vitals together score higher than either alone.

    Returns:
        Float in [0.0, 1.0]. 0.0 = all vitals normal, 1.0 = severely abnormal.
    """
    hr_dev = _deviation_fraction(heart_rate, *NORMAL_HR, hard_span=60)
    spo2_dev = 0.0 if spo2 >= NORMAL_SPO2_MIN else min(1.0, (NORMAL_SPO2_MIN - spo2) / 20)
    temp_dev = _deviation_fraction(temperature, *NORMAL_TEMP, hard_span=3.5)

    worst = max(hr_dev, spo2_dev, temp_dev)
    average = (hr_dev + spo2_dev + temp_dev) / 3
    return round(min(1.0, 0.7 * worst + 0.3 * average), 4)


def score_age_factor(age: int) -> float:
    """
    Score age-based risk contribution.

    Higher for very young (<5) and elderly (>65) patients, reflecting real
    clinical risk stratification — both groups decompensate faster and
    tolerate the same vital deviation less well than a healthy adult.

    Returns:
        Float in [0.0, 1.0].
    """
    if age < 1:
        return 1.0
    if age < 5:
        return round(0.75 - (age / 5) * 0.25, 4)      # 0.75 -> 0.50
    if age <= 65:
        return 0.1
    if age <= 80:
        return round(0.1 + ((age - 65) / 15) * 0.4, 4)  # 0.10 -> 0.50
    return round(min(1.0, 0.5 + ((age - 80) / 20) * 0.5), 4)  # 0.50 -> 1.00+
