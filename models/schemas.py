"""
models/schemas.py

Shared data contract for PatientTriage.ai (MMTG).

Every engine module (NLP classifier, risk engine, vitals/age scoring,
mass casualty queue) reads a `PatientInput` and, directly or indirectly,
contributes to a `TriageResult`. Keep these strict — validation errors
here should surface immediately in the UI, not silently produce a bad
risk score.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


# --------------------------------------------------------------------------- #
# Input
# --------------------------------------------------------------------------- #

class PatientInput(BaseModel):
    """
    First-minute data captured for a patient at ED arrival.

    Only fields realistically available in the first minute belong here —
    resist the urge to add "nice to have" fields once lab results, imaging,
    etc. come back. That's the whole point of the design constraint.
    """

    age: int = Field(
        ...,
        ge=0,
        le=120,
        description="Patient age in years.",
    )
    heart_rate: int = Field(
        ...,
        ge=0,
        le=300,
        description="Heart rate in beats per minute (bpm).",
    )
    spo2: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Blood oxygen saturation, percent (%).",
    )
    temperature: float = Field(
        ...,
        ge=25.0,
        le=45.0,
        description="Body temperature in degrees Celsius. "
        "Range covers severe hypothermia through severe hyperthermia.",
    )
    chief_complaint: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Free-text description of why the patient is here, "
        "captured verbatim at intake.",
    )
    mass_casualty_mode: bool = Field(
        default=False,
        description="When True, the engine MUST bypass the NLP pipeline "
        "entirely and route through the deterministic vitals-only queue.",
    )

    @field_validator("chief_complaint")
    @classmethod
    def complaint_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("chief_complaint cannot be blank or whitespace-only")
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "example": {
                "age": 54,
                "heart_rate": 128,
                "spo2": 91.0,
                "temperature": 37.6,
                "chief_complaint": "Patient clutching chest, says it feels tight",
                "mass_casualty_mode": False,
            }
        }
    }


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #

class ExplainabilityBreakdown(BaseModel):
    """
    Raw sub-scores and their weighted contribution to the final risk score.

    This is what powers the explainability panel — every number here should
    be something the UI can render directly (e.g. as a progress bar) without
    any further computation.
    """

    vital_deviation: float = Field(..., ge=0.0, le=1.0)
    nlp_urgency: float = Field(..., ge=0.0, le=1.0)
    age_factor: float = Field(..., ge=0.0, le=1.0)

    alpha: float = Field(..., description="Weight applied to vital_deviation.")
    beta: float = Field(..., description="Weight applied to nlp_urgency.")
    gamma: float = Field(..., description="Weight applied to age_factor.")

    alpha_contribution: float = Field(
        ..., description="alpha * vital_deviation — this term's share of Risk_Score."
    )
    beta_contribution: float = Field(
        ..., description="beta * nlp_urgency — this term's share of Risk_Score."
    )
    gamma_contribution: float = Field(
        ..., description="gamma * age_factor — this term's share of Risk_Score."
    )


class TriageResult(BaseModel):
    """
    The engine's complete output for one patient.

    `decisions` is intentionally a short list — only narrow, protocol-safe
    auto-actions belong here (the "decide" side of decide-vs-recommend).
    Everything else the system suggests belongs in `esi_level`, which the
    nurse always confirms.
    """

    risk_score: float = Field(
        ..., ge=0.0, le=1.0, description="Final combined MMTG risk score."
    )
    esi_level: int = Field(
        ...,
        ge=1,
        le=5,
        description="Recommended Emergency Severity Index. "
        "1 = most urgent, 5 = least urgent. Always nurse-confirmed.",
    )
    decisions: list[str] = Field(
        default_factory=list,
        description='Narrow, auto-triggered protocol actions, e.g. '
        '"Auto-order ECG + Cardiac Enzyme Panel". Empty in most cases.',
    )
    mass_casualty_mode: bool = Field(
        default=False,
        description="True if this result came from the deterministic "
        "vitals-only bypass queue rather than the full MMTG pipeline.",
    )
    explain: ExplainabilityBreakdown | None = Field(
        default=None,
        description="Full weight breakdown for the explainability panel. "
        "None when mass_casualty_mode is True — that path is rule-based, "
        "not weighted, so there is nothing to attribute to alpha/beta/gamma.",
    )
    reason: str | None = Field(
        default=None,
        description="One-line plain-English reason, primarily used by the "
        "Mass Casualty queue (e.g. 'SpO2 critically low, elevated heart rate').",
    )
