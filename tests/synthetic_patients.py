"""
tests/synthetic_patients.py

Pre-built patient scenarios spanning the risk spectrum — used for
demo, end-to-end testing, and load benchmarking. Each scenario is
clinically justified and includes comments explaining the expected
ESI level and any auto-triggered decisions.
"""

from __future__ import annotations

from dataclasses import dataclass

from models.schemas import PatientInput


@dataclass
class SyntheticScenario:
    """A named test patient with expected outcomes."""

    name: str
    patient: PatientInput
    expected_esi_min: int = 1
    expected_esi_max: int = 5
    expect_decision: bool = False
    clinical_notes: str = ""


# ============================================================================
# Low-risk scenarios (ESI 4–5)
# ============================================================================

LOW_RISK_ANKLE_SPRAIN = SyntheticScenario(
    name="Low-risk ankle sprain",
    patient=PatientInput(
        age=28,
        heart_rate=76,
        spo2=98.0,
        temperature=36.8,
        chief_complaint="Twisted ankle playing football, swelling and mild pain but I can walk on it",
        mass_casualty_mode=False,
    ),
    expected_esi_min=4,
    expected_esi_max=5,
    expect_decision=False,
    clinical_notes="All vitals normal, complaint is minor musculoskeletal injury. "
                   "Delayed triage is acceptable.",
)

LOW_RISK_ROUTINE_CHECKUP = SyntheticScenario(
    name="Routine follow-up, asymptomatic",
    patient=PatientInput(
        age=52,
        heart_rate=72,
        spo2=99.0,
        temperature=36.5,
        chief_complaint="Just checking in for a follow-up visit, feeling fine",
        mass_casualty_mode=False,
    ),
    expected_esi_min=4,
    expected_esi_max=5,
    expect_decision=False,
    clinical_notes="Asymptomatic, normal vitals. Scheduled visit — zero urgency.",
)

# ============================================================================
# Moderate-risk scenarios (ESI 3)
# ============================================================================

MODERATE_RISK_STOMACH_PAIN = SyntheticScenario(
    name="Abdominal pain, mild–moderate",
    patient=PatientInput(
        age=45,
        heart_rate=92,
        spo2=96.0,
        temperature=37.9,
        chief_complaint="Stomach pain for a few hours, feels like indigestion but won't go away",
        mass_casualty_mode=False,
    ),
    expected_esi_min=3,
    expected_esi_max=3,
    expect_decision=False,
    clinical_notes="Slightly elevated temp and heart rate, but complaint is vague. "
                   "Differential is wide — no auto-trigger warranted.",
)

MODERATE_RISK_ELDERLY_DIZZINESS = SyntheticScenario(
    name="Elderly patient, dizziness",
    patient=PatientInput(
        age=78,
        heart_rate=88,
        spo2=94.5,
        temperature=37.0,
        chief_complaint="Feeling dizzy and weak since yesterday, happened once before",
        mass_casualty_mode=False,
    ),
    expected_esi_min=2,
    expected_esi_max=3,
    expect_decision=False,
    clinical_notes="Age >65 drives risk up despite borderline vitals. Dizziness + weakness "
                   "in elderly is a red flag but vague — requires workup, not auto-action.",
)

# ============================================================================
# High-risk scenarios (ESI 1–2, often with decide-triggers)
# ============================================================================

HIGH_RISK_CARDIAC_CRUSHING_CHEST = SyntheticScenario(
    name="High-risk: cardiac emergency",
    patient=PatientInput(
        age=60,
        heart_rate=135,
        spo2=90.0,
        temperature=37.2,
        chief_complaint="Severe chest pain radiating to left arm, feels crushing, started 20 minutes ago",
        mass_casualty_mode=False,
    ),
    expected_esi_min=1,
    expected_esi_max=2,
    expect_decision=True,
    clinical_notes="Classic acute coronary syndrome presentation. High HR, low SpO2, "
                   "classic cardiac language. MUST auto-trigger ECG + troponin.",
)

HIGH_RISK_RESPIRATORY_SEVERE = SyntheticScenario(
    name="High-risk: severe respiratory distress",
    patient=PatientInput(
        age=55,
        heart_rate=118,
        spo2=87.0,
        temperature=38.9,
        chief_complaint="Can't catch my breath, wheezing, chest pain when I breathe, started suddenly",
        mass_casualty_mode=False,
    ),
    expected_esi_min=1,
    expected_esi_max=2,
    expect_decision=True,
    clinical_notes="Critical SpO2 (<90), tachycardia, fever, respiratory keywords all high. "
                   "Likely pneumonia or PE — needs imaging + oxygen prep.",
)

HIGH_RISK_TRAUMA_BLEEDING = SyntheticScenario(
    name="High-risk: major trauma, active bleeding",
    patient=PatientInput(
        age=34,
        heart_rate=145,
        spo2=91.0,
        temperature=36.5,
        chief_complaint="Fell off a ladder 6 feet, leg is badly broken, lots of bleeding, can't move it",
        mass_casualty_mode=False,
    ),
    expected_esi_min=1,
    expected_esi_max=2,
    expect_decision=True,
    clinical_notes="Severe vital deviations + trauma language all high. Hemorrhage risk + "
                   "airway compromise — flag for immediate trauma-bay routing.",
)

HIGH_RISK_INFANT_HIGH_FEVER = SyntheticScenario(
    name="High-risk: febrile infant",
    patient=PatientInput(
        age=1,
        heart_rate=160,
        spo2=96.0,
        temperature=39.8,
        chief_complaint="Baby has had very high fever since last night, very fussy, won't eat",
        mass_casualty_mode=False,
    ),
    expected_esi_min=1,
    expected_esi_max=2,
    expect_decision=False,  # No auto-trigger rule for pediatric fever yet, but high ESI driven by age + temp
    clinical_notes="HR and temperature deviations are severe even for an infant. Age factor "
                   "amplifies risk — sepsis workup needed urgently.",
)

HIGH_RISK_YOUNG_SEVERE_BLEEDING = SyntheticScenario(
    name="High-risk: young patient, severe bleeding",
    patient=PatientInput(
        age=26,
        heart_rate=142,
        spo2=93.0,
        temperature=37.0,
        chief_complaint="Stabbed in the abdomen, bleeding heavily, getting lightheaded",
        mass_casualty_mode=False,
    ),
    expected_esi_min=1,
    expected_esi_max=2,
    expect_decision=True,
    clinical_notes="Massive tachycardia + moderate SpO2 drop indicates hemorrhagic shock. "
                   "Trauma flag + active bleeding — immediate surgical evaluation.",
)

# ============================================================================
# Edge cases
# ============================================================================

EDGE_CASE_SINGLE_WORD_COMPLAINT = SyntheticScenario(
    name="Edge case: minimal complaint",
    patient=PatientInput(
        age=40,
        heart_rate=80,
        spo2=97.0,
        temperature=37.0,
        chief_complaint="pain",
        mass_casualty_mode=False,
    ),
    expected_esi_min=3,
    expected_esi_max=4,
    expect_decision=False,
    clinical_notes="Vitals completely normal; complaint is a single word. "
                   "Should classify as 'Routine' (via fallback if needed) and score low.",
)

EDGE_CASE_HYPOTHERMIA = SyntheticScenario(
    name="Edge case: hypothermia",
    patient=PatientInput(
        age=72,
        heart_rate=52,
        spo2=95.0,
        temperature=32.0,
        chief_complaint="Found outside in the cold, not fully conscious, very weak",
        mass_casualty_mode=False,
    ),
    expected_esi_min=1,
    expected_esi_max=2,
    expect_decision=False,  # No specific hypothermia trigger rule yet
    clinical_notes="Severe temperature deviation + bradycardia + altered mental status. "
                   "Extreme hypothermia — passive rewarming urgent but no aggressive triggers.",
)

# ============================================================================
# Mass Casualty scenarios
# ============================================================================

MASS_CASUALTY_CRITICAL = SyntheticScenario(
    name="Mass casualty: critical (vitals-only)",
    patient=PatientInput(
        age=70,
        heart_rate=140,
        spo2=82.0,
        temperature=38.5,
        chief_complaint="n/a — mass casualty mode, chief complaint not evaluated",
        mass_casualty_mode=True,
    ),
    expected_esi_min=1,
    expected_esi_max=2,
    expect_decision=False,
    clinical_notes="Deterministic mass-casualty ranking: critical vitals place this patient "
                   "at the front of the queue.",
)

MASS_CASUALTY_STABLE = SyntheticScenario(
    name="Mass casualty: stable (vitals-only)",
    patient=PatientInput(
        age=25,
        heart_rate=78,
        spo2=98.0,
        temperature=36.9,
        chief_complaint="n/a — mass casualty mode, chief complaint not evaluated",
        mass_casualty_mode=True,
    ),
    expected_esi_min=4,
    expected_esi_max=5,
    expect_decision=False,
    clinical_notes="Deterministic mass-casualty ranking: normal vitals, no age risk. "
                   "Deferred until more critical patients are triaged.",
)

# ============================================================================
# Scenario collections for different test purposes
# ============================================================================

ALL_SCENARIOS = [
    LOW_RISK_ANKLE_SPRAIN,
    LOW_RISK_ROUTINE_CHECKUP,
    MODERATE_RISK_STOMACH_PAIN,
    MODERATE_RISK_ELDERLY_DIZZINESS,
    HIGH_RISK_CARDIAC_CRUSHING_CHEST,
    HIGH_RISK_RESPIRATORY_SEVERE,
    HIGH_RISK_TRAUMA_BLEEDING,
    HIGH_RISK_INFANT_HIGH_FEVER,
    HIGH_RISK_YOUNG_SEVERE_BLEEDING,
    EDGE_CASE_SINGLE_WORD_COMPLAINT,
    EDGE_CASE_HYPOTHERMIA,
    MASS_CASUALTY_CRITICAL,
    MASS_CASUALTY_STABLE,
]

DEMO_SCENARIOS = [
    LOW_RISK_ANKLE_SPRAIN,
    HIGH_RISK_CARDIAC_CRUSHING_CHEST,
]

HIGH_RISK_SCENARIOS = [s for s in ALL_SCENARIOS if "HIGH_RISK" in s.name.upper()]

MASS_CASUALTY_SCENARIOS = [s for s in ALL_SCENARIOS if s.patient.mass_casualty_mode]


def get_scenario_by_name(name: str) -> SyntheticScenario | None:
    """Fetch a scenario by its name."""
    for scenario in ALL_SCENARIOS:
        if scenario.name.lower() == name.lower():
            return scenario
    return None
