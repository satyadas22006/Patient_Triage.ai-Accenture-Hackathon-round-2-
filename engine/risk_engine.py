"""
engine/risk_engine.py

Owner: Qudsia — Day 2

Baseline implementation is complete and tested. The DAG is modeled as an
explicit class (RiskDAG) rather than a bare formula, so its node structure
is inspectable — a judge can print `RiskDAG().describe()` and see exactly
how a score was built, which is the whole point of choosing a graph over a
black-box model.

Qudsia: the weights, ESI thresholds, and decide-trigger rules below are all
tunable in one place (top of file) — refine them against real/synthetic
data without needing to touch the rest of the pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass

from models.schemas import ExplainabilityBreakdown

# --------------------------------------------------------------------------- #
# Tunable parameters — the whole point of a transparent formula is that these
# live in one place and are easy to defend/adjust.
# --------------------------------------------------------------------------- #

DEFAULT_ALPHA = 0.4   # weight on vital deviation
DEFAULT_BETA = 0.4    # weight on NLP urgency
DEFAULT_GAMMA = 0.2   # weight on age factor

# ESI thresholds: risk_score >= threshold -> that ESI level.
# Checked from most urgent (1) to least urgent (5); first match wins.
ESI_THRESHOLDS = [
    (0.80, 1),
    (0.60, 2),
    (0.40, 3),
    (0.20, 4),
    (0.00, 5),
]


# --------------------------------------------------------------------------- #
# The DAG
# --------------------------------------------------------------------------- #

@dataclass
class RiskNode:
    name: str
    value: float
    weight: float | None = None

    @property
    def contribution(self) -> float:
        return self.value if self.weight is None else self.value * self.weight


class RiskDAG:
    """
    A small, explicit directed acyclic graph:

        Vital_Deviation ---\\
        NLP_Urgency -------- Risk_Score
        Age_Factor  --------/

    Each input node feeds one edge, weighted by alpha/beta/gamma, into a
    single Risk_Score output node. Modeling it this way (rather than a bare
    expression) means `describe()` can render the exact structure a judge
    would want to see in an explainability audit.
    """

    def __init__(self, alpha: float = DEFAULT_ALPHA, beta: float = DEFAULT_BETA,
                 gamma: float = DEFAULT_GAMMA):
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma

    def score(
        self, vital_deviation: float, nlp_urgency: float, age_factor: float
    ) -> tuple[float, ExplainabilityBreakdown]:
        nodes = [
            RiskNode("Vital_Deviation", vital_deviation, self.alpha),
            RiskNode("NLP_Urgency", nlp_urgency, self.beta),
            RiskNode("Age_Factor", age_factor, self.gamma),
        ]
        risk_score = round(min(1.0, sum(n.contribution for n in nodes)), 4)

        breakdown = ExplainabilityBreakdown(
            vital_deviation=vital_deviation,
            nlp_urgency=nlp_urgency,
            age_factor=age_factor,
            alpha=self.alpha,
            beta=self.beta,
            gamma=self.gamma,
            alpha_contribution=round(nodes[0].contribution, 4),
            beta_contribution=round(nodes[1].contribution, 4),
            gamma_contribution=round(nodes[2].contribution, 4),
        )
        return risk_score, breakdown

    def describe(self) -> str:
        return (
            f"RiskDAG(alpha={self.alpha}, beta={self.beta}, gamma={self.gamma}) "
            f"-> Risk_Score = alpha*Vital_Deviation + beta*NLP_Urgency + gamma*Age_Factor"
        )


# --------------------------------------------------------------------------- #
# Public functions (the contract the orchestrator/UI call against)
# --------------------------------------------------------------------------- #

def compute_risk(
    vital_deviation: float,
    nlp_urgency: float,
    age_factor: float,
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
    gamma: float = DEFAULT_GAMMA,
) -> tuple[float, ExplainabilityBreakdown]:
    """
    Combine the three sub-scores into a final risk score via the RiskDAG.

    Returns:
        (risk_score, explainability_breakdown)
    """
    dag = RiskDAG(alpha=alpha, beta=beta, gamma=gamma)
    return dag.score(vital_deviation, nlp_urgency, age_factor)


def map_risk_to_esi(risk_score: float) -> int:
    """
    Map a continuous risk score in [0.0, 1.0] to a discrete ESI level (1-5).

    1 = most urgent, 5 = least urgent. Thresholds are defined in
    ESI_THRESHOLDS above — adjust them there, not here.
    """
    for threshold, esi in ESI_THRESHOLDS:
        if risk_score >= threshold:
            return esi
    return 5  # fallback, should be unreachable given the 0.00 threshold


def check_decide_triggers(
    vital_deviation: float,
    nlp_urgency: float,
    nlp_label: str,
    heart_rate: int,
) -> list[str]:
    """
    Return narrow, high-confidence auto-triggered actions.

    Deliberately conservative — this is the "decide" side of
    decide-vs-recommend, so false positives are costly. Most patients
    return an empty list.
    """
    decisions: list[str] = []

    if nlp_label == "Cardiac" and nlp_urgency >= 0.80 and heart_rate > 120:
        decisions.append("DECISION: Auto-order ECG + Cardiac Enzyme Panel")

    if nlp_label == "Respiratory" and nlp_urgency >= 0.80 and vital_deviation >= 0.5:
        decisions.append("DECISION: Auto-order pulse oximetry re-check + oxygen prep")

    if nlp_label == "Trauma" and vital_deviation >= 0.7:
        decisions.append("DECISION: Flag for immediate trauma-bay routing")

    return decisions
