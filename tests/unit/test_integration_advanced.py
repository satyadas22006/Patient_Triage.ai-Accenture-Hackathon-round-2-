"""
tests/test_integration_advanced.py

Advanced integration tests covering:
- Edge cases (extreme vitals, empty data)
- Concurrency and thread-safety
- Configuration flexibility
- Graceful degradation
"""

from __future__ import annotations

import concurrent.futures
import pytest

from engine.config import AppConfig, RiskEngineConfig
from engine.orchestrator_v2 import run_triage as run_triage_v2, TriageConfig
from models.schemas import PatientInput


class TestEdgeCases:
    """Test handling of edge cases and extreme values."""

    def test_newborn_with_extreme_vitals(self):
        """A newborn with high heart rate (normal) but low SpO2."""
        patient = PatientInput(
            age=0,  # newborn
            heart_rate=160,  # normal for infant
            spo2=88.0,  # low for any age
            temperature=37.0,
            chief_complaint="Labored breathing",
        )
        result, meta = run_triage_v2(patient)
        assert result.esi_level <= 2  # should be high-risk

    def test_elderly_with_bradycardia(self):
        """Elderly patient with slow heart rate (can be normal for age)."""
        patient = PatientInput(
            age=88,
            heart_rate=48,  # slow but not necessarily dangerous for elderly
            spo2=96.0,
            temperature=36.5,
            chief_complaint="Feeling fine, routine checkup",
        )
        result, meta = run_triage_v2(patient)
        # Should not panic just because HR is low — context matters
        assert 1 <= result.esi_level <= 4

    def test_fever_without_other_symptoms(self):
        """High fever but stable vitals otherwise."""
        patient = PatientInput(
            age=35,
            heart_rate=88,
            spo2=98.0,
            temperature=40.2,  # high fever
            chief_complaint="Fever for 2 days, no other complaints",
        )
        result, meta = run_triage_v2(patient)
        assert result.esi_level <= 4  # elevated but manageable

    def test_single_word_chief_complaint(self):
        """Minimal chief complaint — system should not crash."""
        patient = PatientInput(
            age=45,
            heart_rate=80,
            spo2=97.0,
            temperature=37.0,
            chief_complaint="pain",
        )
        result, meta = run_triage_v2(patient)
        # Should produce a result, possibly using fallback
        assert 1 <= result.esi_level <= 5
        # May use fallback classifier but should still work
        assert result.risk_score is not None

    def test_contradictory_vitals(self):
        """Patient with mismatched vitals (e.g. low HR but high temp)."""
        patient = PatientInput(
            age=50,
            heart_rate=52,  # bradycardia
            spo2=99.0,  # excellent
            temperature=39.5,  # fever
            chief_complaint="Unclear symptoms",
        )
        result, meta = run_triage_v2(patient)
        # System should aggregate these without crashing
        assert 1 <= result.esi_level <= 5


class TestConcurrency:
    """Test thread-safety and concurrent processing."""

    def test_concurrent_triage_runs(self):
        """Multiple threads triaging patients simultaneously."""
        patients = [
            PatientInput(
                age=30 + i,
                heart_rate=80 + (i % 20),
                spo2=95.0 + (i % 5),
                temperature=37.0 + (i % 3),
                chief_complaint=f"Symptom variant {i}",
            )
            for i in range(10)
        ]

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(run_triage_v2, p) for p in patients]
            for future in concurrent.futures.as_completed(futures):
                result, meta = future.result()
                results.append((result, meta))

        assert len(results) == len(patients)
        for result, meta in results:
            assert 1 <= result.esi_level <= 5
            assert meta.latency_ms > 0


class TestConfigurability:
    """Test runtime weight adjustment and configuration."""

    def test_custom_weights(self):
        """Override default alpha/beta/gamma."""
        patient = PatientInput(
            age=60,
            heart_rate=120,
            spo2=92.0,
            temperature=38.0,
            chief_complaint="Chest pain",
        )

        # Run with default weights
        result_default, _ = run_triage_v2(patient)

        # Run with elevated NLP weight (beta)
        config_high_nlp = TriageConfig(alpha=0.2, beta=0.7, gamma=0.1)
        result_high_nlp, _ = run_triage_v2(patient, config=config_high_nlp)

        # Results should differ because risk calculation differs
        assert result_default.risk_score != result_high_nlp.risk_score

    def test_weight_sum_greater_than_one(self):
        """Weights don't need to sum to 1.0 (they're clamped)."""
        patient = PatientInput(
            age=45, heart_rate=85, spo2=96.0, temperature=37.0,
            chief_complaint="Minor ache"
        )

        # alpha + beta + gamma > 1.0
        config = TriageConfig(alpha=0.5, beta=0.5, gamma=0.5)
        result, _ = run_triage_v2(patient, config=config)

        # Should still work; max risk is clamped to 1.0
        assert 0.0 <= result.risk_score <= 1.0

    def test_zero_weights(self):
        """Zero out some weights to isolate effects."""
        patient = PatientInput(
            age=60,
            heart_rate=120,
            spo2=88.0,
            temperature=37.5,
            chief_complaint="Chest pain",
        )

        # Vitals-only (no NLP or age)
        config_vitals_only = TriageConfig(alpha=1.0, beta=0.0, gamma=0.0)
        result_vitals_only, _ = run_triage_v2(patient, config=config_vitals_only)

        assert result_vitals_only.explain.beta_contribution == 0.0
        assert result_vitals_only.explain.gamma_contribution == 0.0


class TestGracefulDegradation:
    """Test that the system degrades gracefully under stress."""

    def test_nlp_fallback_on_long_complaint(self):
        """Very long complaint text — system should handle gracefully."""
        long_complaint = " ".join(["symptom"] * 50)  # 50 words to stay under 500 char limit
        patient = PatientInput(
            age=45,
            heart_rate=80,
            spo2=97.0,
            temperature=37.0,
            chief_complaint=long_complaint,
        )
        result, meta = run_triage_v2(patient)
        # Should still produce a valid result
        assert 1 <= result.esi_level <= 5

    def test_unusual_age_values(self):
        """Age at boundary values."""
        for age in [0, 1, 50, 100, 120]:
            patient = PatientInput(
                age=age,
                heart_rate=80,
                spo2=97.0,
                temperature=37.0,
                chief_complaint="Standard complaint",
            )
            result, meta = run_triage_v2(patient)
            assert 1 <= result.esi_level <= 5

    def test_mass_casualty_with_batch(self):
        """Process multiple patients in mass casualty mode efficiently."""
        from engine.mass_casualty import mass_casualty_queue

        patients = [
            PatientInput(
                age=30 + i,
                heart_rate=80 + (i * 5),
                spo2=95.0 - (i * 1.0),
                temperature=37.0,
                chief_complaint="n/a",
                mass_casualty_mode=True,
            )
            for i in range(20)
        ]

        results = mass_casualty_queue(patients)

        # Should be sorted by risk (highest first)
        risk_scores = [r.risk_score for r in results]
        assert risk_scores == sorted(risk_scores, reverse=True)

        # All should have explain=None (rule-based, not weighted)
        for result in results:
            assert result.explain is None
