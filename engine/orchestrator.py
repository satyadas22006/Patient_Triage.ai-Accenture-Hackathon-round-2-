"""
engine/orchestrator.py

Production-grade single entry point for PatientTriage.ai.

Features:
- Normal triage: NLP + vitals + age
- Mass casualty mode: deterministic vitals-only routing
- NLP fallback / graceful degradation
- Explainable risk scoring
- Decision-recommendation coherence
- Latency tracking
- Metrics collection
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

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


# ---------------------------------------------------------------------------
# Decision / recommendation coherence
# ---------------------------------------------------------------------------

# If an automatic clinical decision trigger fires, the recommendation
# cannot be weaker than ESI 2 (Emergent).
DECIDE_TRIGGER_ESI_CEILING = 2


# ---------------------------------------------------------------------------
# NLP timeout configuration
# ---------------------------------------------------------------------------

NLP_TIMEOUT_SECONDS = 5.0


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class TriageError(Exception):
    """Raised when the triage pipeline cannot produce a result."""
    pass


# ---------------------------------------------------------------------------
# Run metadata
# ---------------------------------------------------------------------------

@dataclass
class TriageRunMeta:
    """
    Metadata about how the triage result was produced.

    This is consumed by the Streamlit UI for:
    - NLP fallback status
    - NLP label
    - NLP confidence
    - latency
    - recovery information
    """

    used_nlp_fallback: bool = False
    nlp_confidence: float | None = None
    nlp_label: str | None = None
    latency_ms: float = 0.0
    error_recovery_steps: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

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
        self.enable_decision_coherence_check = (
            enable_decision_coherence_check
        )

    def validate(self) -> None:
        """Validate configuration values."""

        if not (0.0 <= self.alpha <= 1.0):
            raise ValueError(
                f"alpha must be in [0.0, 1.0], got {self.alpha}"
            )

        if not (0.0 <= self.beta <= 1.0):
            raise ValueError(
                f"beta must be in [0.0, 1.0], got {self.beta}"
            )

        if not (0.0 <= self.gamma <= 1.0):
            raise ValueError(
                f"gamma must be in [0.0, 1.0], got {self.gamma}"
            )


# ---------------------------------------------------------------------------
# Main triage pipeline
# ---------------------------------------------------------------------------

def run_triage(
    patient: PatientInput,
    config: TriageConfig | None = None,
) -> tuple[TriageResult, TriageRunMeta]:
    """
    Run the appropriate triage pipeline.

    Normal mode:
        NLP + vitals + age + explainable risk scoring.

    Mass casualty mode:
        Deterministic vitals-only routing with NLP bypassed.

    Returns:
        (TriageResult, TriageRunMeta)

    Raises:
        TriageError:
            If the complete triage pipeline fails.
    """

    # Use defaults when no custom configuration is supplied.
    if config is None:
        config = TriageConfig()

    config.validate()

    # Start latency measurement BEFORE any pipeline work.
    start_time = time.time()

    # Metadata object returned to the UI.
    meta = TriageRunMeta()

    try:

        # ================================================================
        # MASS CASUALTY MODE
        # ================================================================

        if patient.mass_casualty_mode:

            # Mass casualty mode deliberately bypasses NLP.
            result = triage_single_mass_casualty(patient)

            # Record execution latency.
            meta.latency_ms = (
                time.time() - start_time
            ) * 1000

            # Record metrics if enabled.
            if config.enable_metrics:
                record_triage_run(
                    patient,
                    result,
                    meta.latency_ms,
                )

            return result, meta

        # ================================================================
        # NORMAL TRIAGE PIPELINE
        # ================================================================

        # ---------------------------------------------------------------
        # 1. NLP classification
        # ---------------------------------------------------------------

        try:

            (
                nlp_label,
                nlp_confidence,
                used_fallback,
            ) = classify_chief_complaint(
                patient.chief_complaint
            )

            meta.nlp_label = nlp_label
            meta.nlp_confidence = nlp_confidence
            meta.used_nlp_fallback = used_fallback

            if used_fallback:
                meta.error_recovery_steps.append(
                    "NLP model fallback (keyword classifier)"
                )

        except Exception as nlp_error:

            # If the NLP model completely fails, do not crash the
            # entire triage pipeline.
            meta.error_recovery_steps.append(
                f"NLP error recovered: "
                f"{type(nlp_error).__name__}"
            )

            nlp_label = "Routine"
            nlp_confidence = 0.5

            meta.used_nlp_fallback = True
            meta.nlp_label = nlp_label
            meta.nlp_confidence = nlp_confidence

        # ---------------------------------------------------------------
        # 2. Convert NLP result to urgency score
        # ---------------------------------------------------------------

        from engine.nlp_classifier import LABEL_URGENCY_WEIGHT

        nlp_urgency = round(
            nlp_confidence
            * LABEL_URGENCY_WEIGHT[nlp_label],
            4,
        )

        # ---------------------------------------------------------------
        # 3. Vital deviation
        # ---------------------------------------------------------------

        vital_dev = score_vital_deviation(
            patient.age,
            patient.heart_rate,
            patient.spo2,
            patient.temperature,
        )

        # ---------------------------------------------------------------
        # 4. Age factor
        # ---------------------------------------------------------------

        age_factor = score_age_factor(
            patient.age
        )

        # ---------------------------------------------------------------
        # 5. Explainable risk calculation
        # ---------------------------------------------------------------

        risk_score, breakdown = compute_risk(
            vital_dev,
            nlp_urgency,
            age_factor,
            alpha=config.alpha,
            beta=config.beta,
            gamma=config.gamma,
        )

        # ---------------------------------------------------------------
        # 6. Map risk score to ESI
        # ---------------------------------------------------------------

        esi_level = map_risk_to_esi(
            risk_score
        )

        # ---------------------------------------------------------------
        # 7. Automatic decision triggers
        # ---------------------------------------------------------------

        decisions = check_decide_triggers(
            vital_dev,
            nlp_urgency,
            nlp_label,
            patient.heart_rate,
        )

        # ---------------------------------------------------------------
        # 8. Decision / recommendation coherence
        # ---------------------------------------------------------------

        if (
            config.enable_decision_coherence_check
            and decisions
            and esi_level > DECIDE_TRIGGER_ESI_CEILING
        ):

            # If a critical automatic action is triggered,
            # prevent a weaker ESI recommendation.
            esi_level = DECIDE_TRIGGER_ESI_CEILING

            meta.error_recovery_steps.append(
                "ESI corrected for "
                "decision-recommendation coherence"
            )

        # ---------------------------------------------------------------
        # 9. Build final result
        # ---------------------------------------------------------------

        result = TriageResult(
            risk_score=risk_score,
            esi_level=esi_level,
            decisions=decisions,
            mass_casualty_mode=False,
            explain=breakdown,
            reason=None,
        )

        # ---------------------------------------------------------------
        # 10. Record latency
        # ---------------------------------------------------------------

        meta.latency_ms = (
            time.time() - start_time
        ) * 1000

        # ---------------------------------------------------------------
        # 11. Record metrics
        # ---------------------------------------------------------------

        if config.enable_metrics:

            record_triage_run(
                patient,
                result,
                meta.latency_ms,
                nlp_label=nlp_label,
                nlp_confidence=nlp_confidence,
                used_nlp_fallback=meta.used_nlp_fallback,
            )

        return result, meta

    # ====================================================================
    # FINAL ERROR HANDLER
    # ====================================================================

    except Exception as exc:

        # Even failed runs have a latency value.
        meta.latency_ms = (
            time.time() - start_time
        ) * 1000

        raise TriageError(
            "Triage pipeline failed to produce a result. "
            f"Recovery attempts: "
            f"{meta.error_recovery_steps}. "
            f"Error: {exc}"
        ) from exc