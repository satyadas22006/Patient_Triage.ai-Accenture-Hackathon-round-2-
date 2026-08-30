"""
tests/test_engine.py

End-to-end sanity checks for the wired pipeline (normal mode + mass
casualty mode), independent of the Streamlit UI layer.
"""

from engine.orchestrator import run_triage
from engine.mass_casualty import mass_casualty_queue
from models.schemas import PatientInput


def test_normal_mode_produces_explainable_result():
    patient = PatientInput(
        age=54, heart_rate=128, spo2=91.0, temperature=37.6,
        chief_complaint="Patient clutching chest, says it feels tight",
        mass_casualty_mode=False,
    )
    result, meta = run_triage(patient)
    assert result.mass_casualty_mode is False
    assert result.explain is not None
    assert 1 <= result.esi_level <= 5
    assert 0.0 <= result.risk_score <= 1.0


def test_mass_casualty_mode_bypasses_explainability():
    patient = PatientInput(
        age=70, heart_rate=140, spo2=82.0, temperature=38.5,
        chief_complaint="n/a", mass_casualty_mode=True,
    )
    result, meta = run_triage(patient)
    assert result.mass_casualty_mode is True
    assert result.explain is None
    assert result.reason is not None


def test_mass_casualty_queue_ranks_sicker_patient_first():
    critical = PatientInput(
        age=70, heart_rate=140, spo2=82.0, temperature=38.5,
        chief_complaint="n/a", mass_casualty_mode=True,
    )
    healthy = PatientInput(
        age=25, heart_rate=78, spo2=98.0, temperature=36.9,
        chief_complaint="n/a", mass_casualty_mode=True,
    )
    ranked = mass_casualty_queue([healthy, critical])
    assert ranked[0].risk_score > ranked[1].risk_score


def test_high_risk_cardiac_case_triggers_decision():
    patient = PatientInput(
        age=60, heart_rate=135, spo2=90.0, temperature=37.2,
        chief_complaint="Severe chest pain radiating to left arm, feels crushing",
        mass_casualty_mode=False,
    )
    result, meta = run_triage(patient)
    assert result.esi_level <= 2


def test_decide_trigger_never_contradicts_esi_recommendation():
    """
    Regression test for a real bug found during Day-2 integration: this exact
    patient produced a risk_score of 0.5967 (just under the 0.60 ESI-2
    threshold), so the old logic recommended ESI 3 ("Urgent") while
    simultaneously auto-triggering "order an ECG" — a direct contradiction
    between the decide and recommend layers. Any time a decide-trigger
    fires, the ESI level must be <= DECIDE_TRIGGER_ESI_CEILING, full stop.
    """
    patient = PatientInput(
        age=60, heart_rate=135, spo2=90.0, temperature=37.2,
        chief_complaint="Severe chest pain radiating to left arm, feels crushing",
        mass_casualty_mode=False,
    )
    result, meta = run_triage(patient)
    if result.decisions:
        assert result.esi_level <= 2, (
            "A decide-trigger fired but ESI level is weaker than Emergent — "
            "decide and recommend layers are contradicting each other."
        )
