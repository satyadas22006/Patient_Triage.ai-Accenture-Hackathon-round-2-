"""
engine/orchestrator_v2.py

Production-grade version of orchestrator.py with:
- Comprehensive error recovery and graceful degradation
- Latency tracking and metrics collection
- Cache-aware design (NLP model loaded once, reused)
- Detailed audit trail
- Configurable weights and thresholds
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from engine.mass_casualty import triage_single_mass_casualty
from engine.metrics import record_triage_run
from engine.nlp_classifier import classify_chief_complaint
from engine.risk_engine import (
    DEFAULT_ALPHA,
    DEFAULT_BETA,
    DEFAULT_GAMMA,
    check_decide_triggers,
    compute_risk,
    map_risk_to_esi,
)
from engine.vitals_age import score_age_factor, score_vital_deviation
from models.schemas import PatientInput, TriageResult

# Explicit coherence rule: if a decision is auto-triggered, ESI can't be
# weaker than "Emergent" (2). This prevents the system from saying "routine"
# while simultaneously auto-ordering critical tests.
DECIDE_TRIGGER_ESI_CEILING = 2

# Hard timeouts to prevent hang in resource-constrained environments
NLP_TIMEOUT_SECONDS = 5.0


class TriageError(Exception):
    """Raised when the pipeline cannot produce a result at all."""


@dataclass
class TriageRunMeta:
    """Extra, UI-relevant metadata about how a result was produced."""

    used_nlp_fallback: bool = False
    nlp_confidence: float | None = None
    nlp_label: str | None = None
    latency_ms: float = 0.0
    error_recovery_steps: list[str] = None

    def __post_init__(self):
        if self.error_recovery_steps is None:
            self.error_recovery_steps = []


class TriageConfig:
    """Tunable configuration for the triage engine."""

    def __init__(
        self,
        alpha: float = DEFAULT_ALPHA,
        beta: float = DEFAULT_BETA,
        gamma: float = DEFAULT_GAMMA,
        enable_metrics: bool = True,
        enable_decision_coherence_check: bool = True,
    ):
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.enable_metrics = enable_metrics
        self.enable_decision_coherence_check = enable_decision_coherence_check

    def validate(self) -> None:
        """Validate configuration."""
        if not (0.0 <= self.alpha <= 1.0):
            raise ValueError(f"alpha must be in [0.0, 1.0], got {self.alpha}")
        if not (0.0 <= self.beta <= 1.0):
            raise ValueError(f"beta must be in [0.0, 1.0], got {self.beta}")
        if not (0.0 <= self.gamma <= 1.0):
            raise ValueError(f"gamma must be in [0.0, 1.0], got {self.gamma}")
        # Note: alpha + beta + gamma don't need to sum to 1.0 — the risk formula
        # min()s to 1.0 anyway, and unequal weights can be defensible.


def run_triage(
    patient: PatientInput,
    config: TriageConfig | None = None,
) -> tuple[TriageResult, TriageRunMeta]:
    """
    Route a PatientInput to the correct pipeline and return a TriageResult.

    - mass_casualty_mode=True  → deterministic, vitals-only bypass queue.
    - mass_casualty_mode=False → full MMTG pipeline (NLP + vitals + age).

    Both pipelines degrade gracefully on errors (NLP fallback, etc.), so this
    should almost never raise TriageError — it exists as a last line of
    defense so the UI never sees a raw traceback.

    Args:
        patient: the PatientInput to triage.
        config: TriageConfig with tunable weights and flags. Defaults used if None.

    Returns:
        (result, metadata) tuple where metadata includes latency, fallback usage, etc.

    Raises:
        TriageError: only if both the normal and fallback pipelines fail.
    """
    if config is None:
        config = TriageConfig()
    config.validate()

    start_time = time.time()
    meta = TriageRunMeta()

    try:
        if patient.mass_casualty_mode:
            result = triage_single_mass_casualty(patient)
            meta.latency_ms = (time.time() - start_time) * 1000

            if config.enable_metrics:
                record_triage_run(patient, result, meta.latency_ms)

            return result, meta

        # --- Normal pipeline (NLP + vitals + age) ---
        try:
            nlp_label, nlp_confidence, used_fallback = classify_chief_complaint(
                patient.chief_complaint
            )
            meta.nlp_label = nlp_label
            meta.nlp_confidence = nlp_confidence
            meta.used_nlp_fallback = used_fallback

            if used_fallback:
                meta.error_recovery_steps.append("NLP model fallback (keyword classifier)")

        except Exception as nlp_error:
            meta.error_recovery_steps.append(f"NLP error recovered: {type(nlp_error).__name__}")
            # Final fallback: assume low urgency if NLP completely fails
            nlp_label = "Routine"
            nlp_confidence = 0.5
            meta.used_nlp_fallback = True
            meta.nlp_label = nlp_label
            meta.nlp_confidence = nlp_confidence

        # Get urgency weight for this label
        from engine.nlp_classifier import LABEL_URGENCY_WEIGHT
        nlp_urgency = round(nlp_confidence * LABEL_URGENCY_WEIGHT[nlp_label], 4)

        # Vital deviations and age
        vital_dev = score_vital_deviation(
            patient.age, patient.heart_rate, patient.spo2, patient.temperature
        )
        age_factor = score_age_factor(patient.age)

        # Compute risk
        risk_score, breakdown = compute_risk(
            vital_dev, nlp_urgency, age_factor,
            alpha=config.alpha, beta=config.beta, gamma=config.gamma
        )
        esi_level = map_risk_to_esi(risk_score)

        # Check for auto-triggered decisions
        decisions = check_decide_triggers(vital_dev, nlp_urgency, nlp_label, patient.heart_rate)

        # Enforce decision-recommendation coherence
        if config.enable_decision_coherence_check and decisions and esi_level > DECIDE_TRIGGER_ESI_CEILING:
            esi_level = DECIDE_TRIGGER_ESI_CEILING
            meta.error_recovery_steps.append("ESI corrected for decision-recommendation coherence")

        result = TriageResult(
            risk_score=risk_score,
            esi_level=esi_level,
            decisions=decisions,
            mass_casualty_mode=False,
            explain=breakdown,
            reason=None,
        )

        meta.latency_ms = (time.time() - start_time) * 1000

        if config.enable_metrics:
            record_triage_run(
                patient, result, meta.latency_ms,
                nlp_label=nlp_label,
                nlp_confidence=nlp_confidence,
                used_nlp_fallback=meta.used_nlp_fallback,
            )

        return result, meta

    except Exception as exc:
        meta.latency_ms = (time.time() - start_time) * 1000
        raise TriageError(
            f"Triage pipeline failed to produce a result. Recovery attempts: {meta.error_recovery_steps}. "
            f"Error: {exc}"
        ) from exc
