"""
backend/db/models.py

SQLAlchemy ORM models for database persistence.
Defines tables for patients, assessments, and audit logs.
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean, 
    ForeignKey, Text, Enum, Index, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.dialects.postgresql import JSON
import uuid
from enum import Enum as PyEnum

Base = declarative_base()


class ESILevelEnum(int, PyEnum):
    """Emergency Severity Index levels."""
    IMMEDIATE = 1
    EMERGENT = 2
    URGENT = 3
    LESS_URGENT = 4
    MINOR = 5


class TriageModeEnum(str, PyEnum):
    """Triage mode enumeration."""
    NORMAL = "normal"
    MASS_CASUALTY = "mass_casualty"


# ============================================================================
# PATIENT TABLE
# ============================================================================

class Patient(Base):
    """Patient master record."""
    
    __tablename__ = "patients"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, index=True)
    age = Column(Integer, nullable=False)
    gender = Column(String(10), nullable=True)
    medical_record_number = Column(String(50), unique=True, nullable=True, index=True)
    contact_phone = Column(String(20), nullable=True)
    allergies = Column(Text, nullable=True)
    
    # Relationships
    triage_assessments = relationship("TriageAssessment", back_populates="patient", cascade="all, delete-orphan")
    
    # Audit columns
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_archived = Column(Boolean, default=False, index=True)
    
    __table_args__ = (
        Index("idx_patient_mrn_active", "medical_record_number", "is_archived"),
        Index("idx_patient_created", "created_at"),
    )
    
    def __repr__(self):
        return f"<Patient id={self.id} name={self.name} age={self.age}>"


# ============================================================================
# TRIAGE ASSESSMENT TABLE
# ============================================================================

class TriageAssessment(Base):
    """Individual triage assessment record."""
    
    __tablename__ = "triage_assessments"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    
    # Input vitals (echoed for audit trail)
    age = Column(Integer, nullable=False)
    heart_rate = Column(Integer, nullable=False)
    spO2 = Column(Integer, nullable=False)
    temperature = Column(Float, nullable=False)
    chief_complaint = Column(Text, nullable=False)
    
    # Triage result
    esi_level = Column(Enum(ESILevelEnum), nullable=False, index=True)
    esi_color = Column(String(10), nullable=False)  # red, orange, yellow, green, blue
    risk_score = Column(Float, nullable=False)
    
    # Clinical decision
    decision = Column(String(100), nullable=True, index=True)  # e.g., "auto_order_ecg"
    decision_confidence = Column(Float, nullable=True)
    decision_rationale = Column(Text, nullable=True)
    
    # Plain-English reason
    reason = Column(Text, nullable=False)
    
    # Explainability breakdown (stored as JSON)
    explain = Column(JSON, nullable=False)  # Detailed breakdown of factors
    
    # Mode info
    mode = Column(Enum(TriageModeEnum), default=TriageModeEnum.NORMAL, nullable=False)
    
    # Performance metrics
    latency_ms = Column(Float, nullable=False)
    model_version = Column(String(50), nullable=False)
    nlp_fallback_used = Column(Boolean, default=False)
    
    # Location tracking (optional)
    ed_location = Column(String(50), nullable=True)
    
    # Audit columns
    assessment_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    patient = relationship("Patient", back_populates="triage_assessments")
    audit_logs = relationship("AuditLog", back_populates="assessment", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_assessment_patient_created", "patient_id", "created_at"),
        Index("idx_assessment_esi_timestamp", "esi_level", "assessment_timestamp"),
        Index("idx_assessment_decision", "decision"),
    )
    
    def __repr__(self):
        return f"<TriageAssessment id={self.id} patient_id={self.patient_id} esi={self.esi_level}>"


# ============================================================================
# BATCH PROCESSING TABLE
# ============================================================================

class BatchJob(Base):
    """Track batch processing jobs."""
    
    __tablename__ = "batch_jobs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    batch_id = Column(String, nullable=True, index=True)
    
    # Status tracking
    status = Column(String(20), default="pending", index=True)  # pending, processing, completed, failed
    total_patients = Column(Integer, nullable=False)
    successful = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    
    # Performance
    total_latency_ms = Column(Float, nullable=True)
    avg_latency_per_patient_ms = Column(Float, nullable=True)
    
    # Results storage
    results_summary = Column(JSON, nullable=True)  # Summary of results
    errors = Column(JSON, nullable=True)  # Error details
    
    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index("idx_batch_status_created", "status", "created_at"),
    )
    
    def __repr__(self):
        return f"<BatchJob id={self.id} status={self.status} patients={self.total_patients}>"


# ============================================================================
# AUDIT LOG TABLE
# ============================================================================

class AuditLog(Base):
    """Audit trail for all triage assessments."""
    
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id = Column(String, ForeignKey("triage_assessments.id"), nullable=False, index=True)
    
    # Event info
    event_type = Column(String(50), nullable=False, index=True)  # e.g., "assessment_created", "decision_triggered"
    details = Column(JSON, nullable=True)
    
    # Who performed the action (if applicable)
    user_id = Column(String, nullable=True, index=True)
    user_role = Column(String(50), nullable=True)
    
    # Audit metadata
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    assessment = relationship("TriageAssessment", back_populates="audit_logs")
    
    __table_args__ = (
        Index("idx_audit_assessment_event", "assessment_id", "event_type"),
        Index("idx_audit_timestamp", "created_at"),
    )
    
    def __repr__(self):
        return f"<AuditLog id={self.id} assessment_id={self.assessment_id} event={self.event_type}>"


# ============================================================================
# METRICS LOG TABLE
# ============================================================================

class MetricsLog(Base):
    """Time-series metrics for monitoring and analysis."""
    
    __tablename__ = "metrics_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id = Column(String, ForeignKey("triage_assessments.id"), nullable=True, index=True)
    
    # Metrics snapshot
    latency_ms = Column(Float, nullable=False)
    model_inference_ms = Column(Float, nullable=True)
    nlp_processing_ms = Column(Float, nullable=True)
    risk_calculation_ms = Column(Float, nullable=True)
    
    # Model performance
    nlp_fallback_used = Column(Boolean, default=False)
    esi_level = Column(Integer, nullable=False)
    risk_score = Column(Float, nullable=False)
    
    # Vitals processed
    heart_rate = Column(Integer, nullable=False)
    spO2 = Column(Integer, nullable=False)
    temperature = Column(Float, nullable=False)
    
    # Environment
    mode = Column(String(20), nullable=False)  # "normal" or "mass_casualty"
    model_version = Column(String(50), nullable=False)
    
    # Timestamp
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index("idx_metrics_timestamp_esi", "timestamp", "esi_level"),
        Index("idx_metrics_model_version", "model_version", "timestamp"),
    )
    
    def __repr__(self):
        return f"<MetricsLog id={self.id} latency={self.latency_ms:.1f}ms>"


# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

def init_db(database_url: str, echo: bool = False):
    """
    Initialize database engine and create all tables.
    
    Args:
        database_url: SQLAlchemy connection string (e.g., postgresql://user:pass@host/db)
        echo: Enable SQL logging
    
    Returns:
        Engine and SessionLocal factory
    """
    engine = create_engine(database_url, echo=echo, pool_pre_ping=True)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create session factory
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    return engine, SessionLocal


# ============================================================================
# MIGRATION HELPER
# ============================================================================

def migrate_add_columns(engine, **kwargs):
    """
    Helper for adding new columns during migrations.
    Use with Alembic for production deployments.
    """
    from sqlalchemy import text
    
    with engine.connect() as conn:
        with conn.begin():
            # Example: ALTER TABLE patients ADD COLUMN ...
            # conn.execute(text("ALTER TABLE patients ADD COLUMN ..."))
            pass
