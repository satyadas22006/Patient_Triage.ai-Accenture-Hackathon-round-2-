"""
engine/metrics.py

Production-grade logging and metrics collection. Captures triage decisions,
decision triggers, NLP fallback usage, and latency for later analysis.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from models.schemas import PatientInput, TriageResult

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("patienttriage.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("engine")


@dataclass
class TriageMetrics:
    """Metrics captured during a single triage run."""

    timestamp: str
    patient_age: int
    patient_spo2: float
    mass_casualty_mode: bool
    used_nlp_fallback: bool
    risk_score: float
    esi_level: int
    decision_triggered: bool
    num_decisions: int
    latency_ms: float
    nlp_label: str | None = None
    nlp_confidence: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


class MetricsCollector:
    """Thread-safe metrics collector for triage runs."""

    def __init__(self, output_path: Path | None = None):
        self.output_path = output_path or Path("triage_metrics.jsonl")
        self.metrics: list[TriageMetrics] = []

    def record(self, metrics: TriageMetrics) -> None:
        """Record a triage run's metrics."""
        self.metrics.append(metrics)
        self._write_jsonl(metrics)
        logger.info(
            f"Triage run recorded: age={metrics.patient_age}, "
            f"ESI={metrics.esi_level}, risk={metrics.risk_score:.2f}, "
            f"latency={metrics.latency_ms:.1f}ms"
        )

    def _write_jsonl(self, metrics: TriageMetrics) -> None:
        """Append metrics to JSONL file for later analysis."""
        with open(self.output_path, "a") as f:
            f.write(metrics.to_json() + "\n")

    def get_summary(self) -> dict[str, Any]:
        """Return summary statistics across all recorded runs."""
        if not self.metrics:
            return {}

        all_risks = [m.risk_score for m in self.metrics]
        all_latencies = [m.latency_ms for m in self.metrics]
        triggered_decisions = [m for m in self.metrics if m.decision_triggered]

        return {
            "total_runs": len(self.metrics),
            "avg_risk_score": sum(all_risks) / len(all_risks),
            "min_risk_score": min(all_risks),
            "max_risk_score": max(all_risks),
            "avg_latency_ms": sum(all_latencies) / len(all_latencies),
            "max_latency_ms": max(all_latencies),
            "decision_trigger_rate": len(triggered_decisions) / len(self.metrics),
            "nlp_fallback_rate": sum(1 for m in self.metrics if m.used_nlp_fallback) / len(self.metrics),
            "mass_casualty_runs": sum(1 for m in self.metrics if m.mass_casualty_mode),
        }


# Global singleton
_collector: MetricsCollector | None = None


def get_collector() -> MetricsCollector:
    """Get or create the global metrics collector."""
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector


def record_triage_run(
    patient: PatientInput,
    result: TriageResult,
    latency_ms: float,
    nlp_label: str | None = None,
    nlp_confidence: float | None = None,
    used_nlp_fallback: bool = False,
) -> None:
    """Convenience function to record a triage run."""
    metrics = TriageMetrics(
        timestamp=datetime.utcnow().isoformat(),
        patient_age=patient.age,
        patient_spo2=patient.spo2,
        mass_casualty_mode=result.mass_casualty_mode,
        used_nlp_fallback=used_nlp_fallback,
        risk_score=result.risk_score,
        esi_level=result.esi_level,
        decision_triggered=len(result.decisions) > 0,
        num_decisions=len(result.decisions),
        latency_ms=latency_ms,
        nlp_label=nlp_label,
        nlp_confidence=nlp_confidence,
    )
    get_collector().record(metrics)
