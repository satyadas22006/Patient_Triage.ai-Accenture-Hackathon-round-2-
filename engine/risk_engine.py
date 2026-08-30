"""
engine/risk_engine.py

Transparent and explainable risk engine for PatientTriage.ai.

The RiskDAG combines:

    Vital Deviation
    NLP Urgency
    Age Factor
          ↓
      Risk Score
          ↓
         ESI

The decision layer separately evaluates narrow, high-confidence
automatic actions.
"""

from __future__ import annotations

from dataclasses import dataclass

from models.schemas import ExplainabilityBreakdown


# ============================================================================
# DEFAULT WEIGHTS
# ============================================================================

DEFAULT_ALPHA = 0.4
DEFAULT_BETA = 0.4
DEFAULT_GAMMA = 0.2


# ============================================================================
# ESI THRESHOLDS
# ============================================================================

ESI_THRESHOLDS = [
    (0.80, 1),
    (0.60, 2),
    (0.40, 3),
    (0.20, 4),
    (0.00, 5),
]


# ============================================================================
# RISK NODE
# ============================================================================

@dataclass
class RiskNode:
    """One node in the explainable risk DAG."""

    name: str
    value: float
    weight: float | None = None

    @property
    def contribution(self) -> float:
        """Weighted contribution of this node."""

        if self.weight is None:
            return self.value

        return self.value * self.weight


# ============================================================================
# RISK DAG
# ============================================================================

class RiskDAG:
    """
    Explicit risk DAG:

        Vital_Deviation ─────┐
                             │
        NLP_Urgency ─────────┼──> Risk_Score
                             │
        Age_Factor ──────────┘
    """

    def __init__(
        self,
        alpha: float = DEFAULT_ALPHA,
        beta: float = DEFAULT_BETA,
        gamma: float = DEFAULT_GAMMA,
    ):
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma

    def score(
        self,
        vital_deviation: float,
        nlp_urgency: float,
        age_factor: float,
    ) -> tuple[float, ExplainabilityBreakdown]:

        nodes = [
            RiskNode(
                "Vital_Deviation",
                vital_deviation,
                self.alpha,
            ),
            RiskNode(
                "NLP_Urgency",
                nlp_urgency,
                self.beta,
            ),
            RiskNode(
                "Age_Factor",
                age_factor,
                self.gamma,
            ),
        ]

        risk_score = round(
            min(
                1.0,
                sum(
                    node.contribution
                    for node in nodes
                ),
            ),
            4,
        )

        breakdown = ExplainabilityBreakdown(
            vital_deviation=vital_deviation,
            nlp_urgency=nlp_urgency,
            age_factor=age_factor,
            alpha=self.alpha,
            beta=self.beta,
            gamma=self.gamma,
            alpha_contribution=round(
                nodes[0].contribution,
                4,
            ),
            beta_contribution=round(
                nodes[1].contribution,
                4,
            ),
            gamma_contribution=round(
                nodes[2].contribution,
                4,
            ),
        )

        return (
            risk_score,
            breakdown,
        )

    def describe(self) -> str:
        """Return a human-readable DAG description."""

        return (
            f"RiskDAG("
            f"alpha={self.alpha}, "
            f"beta={self.beta}, "
            f"gamma={self.gamma}"
            f") -> "
            f"Risk_Score = "
            f"alpha*Vital_Deviation + "
            f"beta*NLP_Urgency + "
            f"gamma*Age_Factor"
        )


# ============================================================================
# PUBLIC RISK CALCULATION
# ============================================================================

def compute_risk(
    vital_deviation: float,
    nlp_urgency: float,
    age_factor: float,
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
    gamma: float = DEFAULT_GAMMA,
) -> tuple[float, ExplainabilityBreakdown]:
    """Compute risk score and explainability breakdown."""

    dag = RiskDAG(
        alpha=alpha,
        beta=beta,
        gamma=gamma,
    )

    return dag.score(
        vital_deviation,
        nlp_urgency,
        age_factor,
    )


# ============================================================================
# ESI MAPPING
# ============================================================================

def map_risk_to_esi(
    risk_score: float,
) -> int:
    """
    Map risk score [0, 1] to ESI 1–5.
    """

    risk_score = max(
        0.0,
        min(
            1.0,
            float(risk_score),
        ),
    )

    for threshold, esi in ESI_THRESHOLDS:

        if risk_score >= threshold:
            return esi

    return 5


# ============================================================================
# DECISION ENGINE
# ============================================================================

def check_decide_triggers(
    vital_deviation: float,
    nlp_urgency: float,
    nlp_label: str,
    heart_rate: int,
) -> list[str]:
    """
    Evaluate narrow high-confidence automatic actions.

    The decision layer intentionally combines:
        - NLP category
        - objective physiological evidence

    It does not depend on NLP urgency confidence alone.
    """

    decisions: list[str] = []

    # Normalize the label defensively.
    label = str(nlp_label).strip().lower()

    # ------------------------------------------------------------------------
    # CARDIAC
    # ------------------------------------------------------------------------
    #
    # Strong cardiac category + objective abnormality.
    #
    # The cardiac emergency demo case:
    #
    #     Cardiac
    #     HR > 120
    #     significant vital deviation
    #
    # should trigger this decision.
    #
    if (
        label == "cardiac"
        and heart_rate > 120
        and vital_deviation >= 0.5
    ):
        decisions.append(
            "DECISION: Auto-order ECG + Cardiac Enzyme Panel"
        )

    # ------------------------------------------------------------------------
    # RESPIRATORY
    # ------------------------------------------------------------------------

    elif (
        label == "respiratory"
        and vital_deviation >= 0.5
    ):
        decisions.append(
            "DECISION: Auto-order pulse oximetry re-check + oxygen prep"
        )

    # ------------------------------------------------------------------------
    # TRAUMA
    # ------------------------------------------------------------------------

    elif (
        label == "trauma"
        and vital_deviation >= 0.7
    ):
        decisions.append(
            "DECISION: Flag for immediate trauma-bay routing"
        )

    return decisions