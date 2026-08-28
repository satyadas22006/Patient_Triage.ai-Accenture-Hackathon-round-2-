"""
tests/test_schemas.py

Sanity checks for the shared data contract. Extend this on Day 3 with the
end-to-end scenario tests once engine modules are implemented.
"""

import pytest
from pydantic import ValidationError

from models.schemas import PatientInput


def test_valid_patient_input():
    p = PatientInput(
        age=54,
        heart_rate=128,
        spo2=91.0,
        temperature=37.6,
        chief_complaint="Patient clutching chest, says it feels tight",
    )
    assert p.mass_casualty_mode is False


def test_blank_chief_complaint_rejected():
    with pytest.raises(ValidationError):
        PatientInput(
            age=54,
            heart_rate=128,
            spo2=91.0,
            temperature=37.6,
            chief_complaint="   ",
        )


def test_out_of_range_spo2_rejected():
    with pytest.raises(ValidationError):
        PatientInput(
            age=54,
            heart_rate=128,
            spo2=150.0,  # invalid — > 100%
            temperature=37.6,
            chief_complaint="Fever and chills",
        )
