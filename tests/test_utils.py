"""
tests/test_utils.py

Testing utilities: synthetic patient generation, batch processing,
statistical analysis, and performance benchmarking.
"""

from __future__ import annotations

import random
import statistics
import time
from dataclasses import dataclass
from typing import Callable

from engine.orchestrator import run_triage
from models.schemas import PatientInput, TriageResult


@dataclass
class TriagePerformanceBench:
    """Results from a performance benchmark run."""

    num_runs: int
    total_time_ms: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float

    @property
    def throughput_per_second(self) -> float:
        """Approximate throughput in patients per second."""
        return 1000.0 / self.avg_latency_ms if self.avg_latency_ms > 0 else 0.0


def benchmark_triage_pipeline(
    patients: list[PatientInput],
    iterations: int = 1,
) -> TriagePerformanceBench:
    """
    Benchmark the triage pipeline against a list of patients.

    Args:
        patients: list of PatientInput to triage.
        iterations: number of times to repeat the test (for stable stats).

    Returns:
        TriagePerformanceBench with latency percentiles.
    """
    latencies: list[float] = []

    for _ in range(iterations):
        for patient in patients:
            start = time.time()
            _ = run_triage(patient)
            latencies.append((time.time() - start) * 1000)

    latencies.sort()

    return TriagePerformanceBench(
        num_runs=len(latencies),
        total_time_ms=sum(latencies),
        avg_latency_ms=statistics.mean(latencies),
        p50_latency_ms=latencies[len(latencies) // 2],
        p95_latency_ms=latencies[int(len(latencies) * 0.95)],
        p99_latency_ms=latencies[int(len(latencies) * 0.99)],
        min_latency_ms=min(latencies),
        max_latency_ms=max(latencies),
    )


class SyntheticPatientFactory:
    """Factory for generating synthetic patients with controlled properties."""

    @staticmethod
    def low_risk_patient(age: int | None = None, seed: int | None = None) -> PatientInput:
        """Generate a low-risk patient (ESI 4–5)."""
        if seed is not None:
            random.seed(seed)
        return PatientInput(
            age=age or random.randint(20, 60),
            heart_rate=random.randint(60, 100),
            spo2=random.uniform(95.0, 100.0),
            temperature=random.uniform(36.5, 37.2),
            chief_complaint="Minor ache, no urgency",
        )

    @staticmethod
    def moderate_risk_patient(age: int | None = None, seed: int | None = None) -> PatientInput:
        """Generate a moderate-risk patient (ESI 3)."""
        if seed is not None:
            random.seed(seed)
        return PatientInput(
            age=age or random.randint(30, 70),
            heart_rate=random.randint(100, 110),
            spo2=random.uniform(93.0, 96.0),
            temperature=random.uniform(37.2, 38.5),
            chief_complaint="Feeling unwell, some symptoms",
        )

    @staticmethod
    def high_risk_patient(age: int | None = None, seed: int | None = None) -> PatientInput:
        """Generate a high-risk patient (ESI 1–2)."""
        if seed is not None:
            random.seed(seed)
        return PatientInput(
            age=age or random.randint(40, 85),
            heart_rate=random.randint(120, 160),
            spo2=random.uniform(85.0, 92.0),
            temperature=random.uniform(38.5, 40.5),
            chief_complaint="Severe chest pain, shortness of breath, emergency",
        )

    @staticmethod
    def elderly_patient(seed: int | None = None) -> PatientInput:
        """Generate an elderly patient with age-related risk elevation."""
        if seed is not None:
            random.seed(seed)
        return PatientInput(
            age=random.randint(75, 95),
            heart_rate=random.randint(75, 120),
            spo2=random.uniform(92.0, 97.0),
            temperature=random.uniform(36.5, 38.0),
            chief_complaint="Feeling weak, dizziness",
        )

    @staticmethod
    def mass_casualty_patient(seed: int | None = None) -> PatientInput:
        """Generate a patient for mass casualty mode testing."""
        if seed is not None:
            random.seed(seed)
        return PatientInput(
            age=random.randint(18, 80),
            heart_rate=random.randint(60, 150),
            spo2=random.uniform(80.0, 99.0),
            temperature=random.uniform(36.0, 40.0),
            chief_complaint="n/a",
            mass_casualty_mode=True,
        )


@dataclass
class TriageOutcomeDistribution:
    """Aggregate outcomes across a batch of triage runs."""

    total_runs: int
    esi_counts: dict[int, int]  # ESI level -> count
    decision_trigger_rate: float
    avg_risk_score: float


def analyze_triage_outcomes(
    patients: list[PatientInput],
) -> TriageOutcomeDistribution:
    """
    Triage a batch of patients and compute aggregate statistics.

    Args:
        patients: list of PatientInput.

    Returns:
        TriageOutcomeDistribution with counts and rates.
    """
    esi_counts = {i: 0 for i in range(1, 6)}
    total_risk = 0.0
    num_decisions = 0

    for patient in patients:
        result, _ = run_triage(patient)
        esi_counts[result.esi_level] += 1
        total_risk += result.risk_score
        if result.decisions:
            num_decisions += 1

    return TriageOutcomeDistribution(
        total_runs=len(patients),
        esi_counts=esi_counts,
        decision_trigger_rate=num_decisions / len(patients) if patients else 0.0,
        avg_risk_score=total_risk / len(patients) if patients else 0.0,
    )


def stress_test_pipeline(
    num_patients: int = 100,
    risk_distribution: str = "uniform",
) -> dict:
    """
    Stress-test the pipeline with a large batch of synthetic patients.

    Args:
        num_patients: how many patients to triage.
        risk_distribution: "uniform" (mix of risks), "low", "high", or "elderly".

    Returns:
        dict with benchmark results and outcome analysis.
    """
    factory = SyntheticPatientFactory()
    patients = []

    if risk_distribution == "uniform":
        for i in range(num_patients):
            choice = i % 4
            if choice == 0:
                patients.append(factory.low_risk_patient(seed=i))
            elif choice == 1:
                patients.append(factory.moderate_risk_patient(seed=i))
            elif choice == 2:
                patients.append(factory.high_risk_patient(seed=i))
            else:
                patients.append(factory.elderly_patient(seed=i))
    elif risk_distribution == "low":
        patients = [factory.low_risk_patient(seed=i) for i in range(num_patients)]
    elif risk_distribution == "high":
        patients = [factory.high_risk_patient(seed=i) for i in range(num_patients)]
    elif risk_distribution == "elderly":
        patients = [factory.elderly_patient(seed=i) for i in range(num_patients)]

    bench = benchmark_triage_pipeline(patients, iterations=1)
    outcomes = analyze_triage_outcomes(patients)

    return {
        "benchmark": bench,
        "outcomes": outcomes,
        "risk_distribution": risk_distribution,
    }
