"""
backend/config.py

Backend configuration management.
Supports environment variables, .env files, and runtime configuration.
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from enum import Enum


class EnvironmentType(str, Enum):
    """Environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env file.
    
    Priority:
    1. Environment variables
    2. .env file
    3. Default values
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # ========================================================================
    # APPLICATION
    # ========================================================================
    
    APP_NAME: str = "PatientTriage.ai"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: EnvironmentType = EnvironmentType.DEVELOPMENT
    DEBUG: bool = True
    
    # ========================================================================
    # API SERVER
    # ========================================================================
    
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4
    API_TIMEOUT: int = 120
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8501",  # Streamlit
        "http://127.0.0.1:8000",
    ]
    
    # ========================================================================
    # DATABASE
    # ========================================================================
    
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_NAME: str = "patienttriage_ai"
    
    # Connection pool
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    DB_POOL_RECYCLE: int = 3600
    DB_POOL_PRE_PING: bool = True
    
    @property
    def DATABASE_URL(self) -> str:
        """Construct database URL."""
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@"
            f"{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )
    
    @property
    def DATABASE_URL_ASYNC(self) -> str:
        """Construct async database URL."""
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@"
            f"{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )
    
    # ========================================================================
    # NLP MODEL CONFIGURATION
    # ========================================================================
    
    NLP_MODEL_NAME: str = "facebook/bart-large-mnli"
    NLP_MODEL_PATH: Optional[str] = None  # Override with local path if provided
    NLP_DEVICE: str = "cuda"  # cuda, cpu, mps
    NLP_TIMEOUT: float = 30.0  # seconds
    NLP_BATCH_SIZE: int = 32
    NLP_MAX_LENGTH: int = 512
    
    # Cache
    NLP_CACHE_DIR: str = "models/cache"
    NLP_ENABLE_CACHE: bool = True
    
    # ========================================================================
    # RISK ENGINE CONFIGURATION
    # ========================================================================
    
    # Weight factors (α + β + γ = 1.0)
    RISK_ALPHA: float = 0.5   # Vital deviations weight
    RISK_BETA: float = 0.35   # NLP urgency weight
    RISK_GAMMA: float = 0.15  # Age factor weight
    
    # Thresholds
    RISK_THRESHOLD_IMMEDIATE: float = 0.85
    RISK_THRESHOLD_EMERGENT: float = 0.70
    RISK_THRESHOLD_URGENT: float = 0.55
    RISK_THRESHOLD_LESS_URGENT: float = 0.30
    
    # ========================================================================
    # DECISION ENGINE CONFIGURATION
    # ========================================================================
    
    # Decision trigger confidence thresholds
    DECISION_CONFIDENCE_THRESHOLD: float = 0.80
    DECISION_REQUIRE_ESI_EMERGENT: bool = True  # Decisions only for ESI 1-2
    
    # ========================================================================
    # MASS CASUALTY MODE
    # ========================================================================
    
    MASS_CASUALTY_MODE: bool = False
    MC_HR_THRESHOLD: int = 130
    MC_SPO2_THRESHOLD: int = 91
    MC_TEMP_THRESHOLD: float = 38.5
    
    # ========================================================================
    # METRICS & MONITORING
    # ========================================================================
    
    METRICS_ENABLED: bool = True
    METRICS_LOG_FILE: str = "logs/triage_metrics.jsonl"
    METRICS_RETENTION_DAYS: int = 90
    
    # Prometheus
    PROMETHEUS_ENABLED: bool = True
    PROMETHEUS_PORT: int = 8001
    
    # ========================================================================
    # LOGGING
    # ========================================================================
    
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: str = "logs/app.log"
    LOG_FILE_ENABLED: bool = True
    LOG_FILE_SIZE_MB: int = 100
    LOG_FILE_BACKUP_COUNT: int = 10
    
    # ========================================================================
    # SECURITY & AUTHENTICATION
    # ========================================================================
    
    API_KEY_REQUIRED: bool = False  # Set to True in production
    API_KEY_HEADER: str = "X-API-Key"
    VALID_API_KEYS: List[str] = []  # Load from environment: "key1,key2,key3"
    
    # JWT (if using auth)
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # ========================================================================
    # CACHING
    # ========================================================================
    
    CACHE_ENABLED: bool = True
    CACHE_BACKEND: str = "memory"  # memory, redis
    CACHE_REDIS_URL: Optional[str] = None
    CACHE_TTL_SECONDS: int = 3600
    
    # ========================================================================
    # BATCH PROCESSING
    # ========================================================================
    
    BATCH_MAX_SIZE: int = 10000
    BATCH_TIMEOUT_SECONDS: int = 300
    BATCH_QUEUE_SIZE: int = 100
    
    # ========================================================================
    # MLFLOW (Experiment Tracking)
    # ========================================================================
    
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"
    MLFLOW_EXPERIMENT_NAME: str = "PatientTriage_Production"
    MLFLOW_ENABLED: bool = True
    
    # ========================================================================
    # DEPLOYMENT
    # ========================================================================
    
    # Kubernetes
    KUBERNETES_ENABLED: bool = False
    KUBERNETES_NAMESPACE: str = "default"
    
    # Docker
    DOCKER_REGISTRY: str = "docker.io"
    DOCKER_IMAGE_NAME: str = "patienttriage-ai"
    DOCKER_IMAGE_TAG: str = "latest"
    
    # ========================================================================
    # FEATURE FLAGS
    # ========================================================================
    
    FEATURE_BATCH_PROCESSING: bool = True
    FEATURE_PATIENT_HISTORY: bool = True
    FEATURE_AUDIT_LOGGING: bool = True
    FEATURE_METRICS_DASHBOARD: bool = True
    FEATURE_ADVANCED_EXPLAINABILITY: bool = True
    
    # ========================================================================
    # METHODS
    # ========================================================================
    
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.ENVIRONMENT == EnvironmentType.PRODUCTION
    
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.ENVIRONMENT == EnvironmentType.DEVELOPMENT
    
    def get_log_file(self) -> str:
        """Get full path to log file."""
        import os
        os.makedirs(os.path.dirname(self.LOG_FILE), exist_ok=True)
        return self.LOG_FILE


# ============================================================================
# INSTANTIATE SETTINGS
# ============================================================================

settings = Settings()

# ============================================================================
# EXAMPLE .env FILE
# ============================================================================

"""
# .env file template (copy to .env and fill in values)

# Application
APP_NAME=PatientTriage.ai
ENVIRONMENT=production
DEBUG=false

# API Server
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Database
DB_HOST=postgres.production.local
DB_PORT=5432
DB_USER=patienttriage_user
DB_PASSWORD=your-secure-password
DB_NAME=patienttriage_ai_prod

# NLP Model
NLP_MODEL_NAME=facebook/bart-large-mnli
NLP_DEVICE=cuda
NLP_TIMEOUT=30.0

# Risk Engine Weights
RISK_ALPHA=0.50
RISK_BETA=0.35
RISK_GAMMA=0.15

# Security
API_KEY_REQUIRED=true
VALID_API_KEYS=key1,key2,key3

# Logging
LOG_LEVEL=INFO
LOG_FILE_ENABLED=true

# MLflow
MLFLOW_TRACKING_URI=http://mlflow.production.local:5000
MLFLOW_ENABLED=true

# Monitoring
PROMETHEUS_ENABLED=true
METRICS_ENABLED=true

# Features
FEATURE_BATCH_PROCESSING=true
FEATURE_AUDIT_LOGGING=true
"""


def load_settings_from_env() -> Settings:
    """Explicitly load settings from environment."""
    return Settings()


def override_settings(**kwargs) -> Settings:
    """
    Override settings at runtime.
    Useful for testing.
    
    Example:
        test_settings = override_settings(DEBUG=True, ENVIRONMENT="testing")
    """
    current = Settings()
    for key, value in kwargs.items():
        if hasattr(current, key):
            setattr(current, key, value)
    return current
