"""
engine/config.py

Centralized configuration management with environment variable support,
validation, and runtime adjustability.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class EnvironmentType(str, Enum):
    """Deployment environment type."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class NLPConfig:
    """Configuration for the NLP urgency classifier."""

    model_name: str = "facebook/bart-large-mnli"
    cache_dir: Path = Path.home() / ".cache" / "huggingface"
    enable_fallback: bool = True
    timeout_seconds: float = 5.0
    device: str = "cpu"  # "cpu" or "cuda"

    @classmethod
    def from_env(cls) -> NLPConfig:
        """Load configuration from environment variables."""
        return cls(
            model_name=os.getenv("NLP_MODEL", "facebook/bart-large-mnli"),
            cache_dir=Path(os.getenv("NLP_CACHE", Path.home() / ".cache" / "huggingface")),
            enable_fallback=os.getenv("NLP_FALLBACK", "true").lower() == "true",
            timeout_seconds=float(os.getenv("NLP_TIMEOUT", "5.0")),
            device=os.getenv("NLP_DEVICE", "cpu"),
        )


@dataclass
class RiskEngineConfig:
    """Configuration for the risk engine (DAG) and ESI mapping."""

    alpha: float = 0.4  # Vital deviation weight
    beta: float = 0.4   # NLP urgency weight
    gamma: float = 0.2  # Age factor weight

    esi_thresholds: dict[int, float] = None

    def __post_init__(self):
        if self.esi_thresholds is None:
            # Default ESI thresholds
            self.esi_thresholds = {
                1: 0.80,  # Resuscitation
                2: 0.60,  # Emergent
                3: 0.40,  # Urgent
                4: 0.20,  # Less Urgent
                5: 0.00,  # Non-Urgent
            }

    @classmethod
    def from_env(cls) -> RiskEngineConfig:
        """Load configuration from environment variables."""
        return cls(
            alpha=float(os.getenv("RISK_ALPHA", "0.4")),
            beta=float(os.getenv("RISK_BETA", "0.4")),
            gamma=float(os.getenv("RISK_GAMMA", "0.2")),
        )


@dataclass
class MetricsConfig:
    """Configuration for metrics collection and logging."""

    enabled: bool = True
    output_path: Path = Path("triage_metrics.jsonl")
    log_level: str = "INFO"
    log_file: Path = Path("patienttriage.log")

    @classmethod
    def from_env(cls) -> MetricsConfig:
        """Load configuration from environment variables."""
        return cls(
            enabled=os.getenv("METRICS_ENABLED", "true").lower() == "true",
            output_path=Path(os.getenv("METRICS_PATH", "triage_metrics.jsonl")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=Path(os.getenv("LOG_FILE", "patienttriage.log")),
        )


@dataclass
class AppConfig:
    """Top-level application configuration."""

    environment: EnvironmentType = EnvironmentType.DEVELOPMENT
    nlp: NLPConfig = None
    risk_engine: RiskEngineConfig = None
    metrics: MetricsConfig = None
    debug: bool = False

    def __post_init__(self):
        if self.nlp is None:
            self.nlp = NLPConfig.from_env()
        if self.risk_engine is None:
            self.risk_engine = RiskEngineConfig.from_env()
        if self.metrics is None:
            self.metrics = MetricsConfig.from_env()

    @classmethod
    def from_env(cls) -> AppConfig:
        """Load full configuration from environment."""
        env_str = os.getenv("ENVIRONMENT", "development").lower()
        environment = EnvironmentType(env_str)

        return cls(
            environment=environment,
            nlp=NLPConfig.from_env(),
            risk_engine=RiskEngineConfig.from_env(),
            metrics=MetricsConfig.from_env(),
            debug=os.getenv("DEBUG", "false").lower() == "true",
        )

    def validate(self) -> None:
        """Validate configuration parameters."""
        assert 0.0 <= self.risk_engine.alpha <= 1.0
        assert 0.0 <= self.risk_engine.beta <= 1.0
        assert 0.0 <= self.risk_engine.gamma <= 1.0
        assert self.nlp.timeout_seconds > 0
        assert self.nlp.device in ("cpu", "cuda")

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "environment": self.environment.value,
            "debug": self.debug,
            "nlp": {
                "model": self.nlp.model_name,
                "device": self.nlp.device,
                "fallback_enabled": self.nlp.enable_fallback,
                "timeout_s": self.nlp.timeout_seconds,
            },
            "risk_engine": {
                "alpha": self.risk_engine.alpha,
                "beta": self.risk_engine.beta,
                "gamma": self.risk_engine.gamma,
            },
            "metrics": {
                "enabled": self.metrics.enabled,
                "log_level": self.metrics.log_level,
            },
        }


# Global config singleton
_app_config: AppConfig | None = None


def get_config() -> AppConfig:
    """Get or initialize the global application config."""
    global _app_config
    if _app_config is None:
        _app_config = AppConfig.from_env()
        _app_config.validate()
    return _app_config


def reload_config() -> AppConfig:
    """Reload configuration from environment (for testing)."""
    global _app_config
    _app_config = AppConfig.from_env()
    _app_config.validate()
    return _app_config
