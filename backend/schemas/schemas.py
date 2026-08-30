"""
backend/schemas.py

Pydantic models for request/response validation.
Defines all data structures exchanged via the API.
"""

from datetime import datetime
from typing import Optional, Dict, List, Literal
from pydantic import BaseModel, Field, validator
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class ESILevel(int, Enum):
    """Emergency Severity Index levels."""
    IMMEDIATE = 1
    EMERGENT = 2
    URGENT = 3
    LESS_URGENT = 4
    MINOR = 5


class ESIColor(str, Enum):
    """ESI color codes for UI rendering."""
    RED = "red"
    ORANGE = "orange"
    YELLOW = "yellow"
    GREEN = "green"
    BLUE = "blue"


class TriageDecision(str, Enum):
    """Possible auto-triggered clinical decisions."""
    ECG_AND_CARDIAC_PANEL = "auto_order_ecg_cardiac_panel"
    OXYGEN_PREP = "auto_prep_oxygen"
    TRAUMA_BAY = "auto_route_trauma_bay"
    STROKE_ALERT = "auto_activate_stroke_alert"
    SEPSIS_PROTOCOL = "auto_initiate_sepsis_protocol"
    PEDS_RESUSCITATION = "auto_peds_resuscitation_prep"
    NONE = "none"


class TriageMode(str, Enum):
    """Triage assessment mode."""
    NORMAL = "normal"
    MASS_CASUALTY = "mass_casualty"


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class TriageAssessmentRequest(BaseModel):
    """Single patient triage assessment request."""
    
    age: int = Field(..., ge=1, le=120, description="Patient age in years")
    heart_rate: int = Field(..., ge=30, le=250, description="Heart rate in bpm")
    spO2: int = Field(..., ge=50, le=100, description="SpO2 in percent")
    temperature: float = Field(..., ge=35.0, le=42.0, description="Temperature in Celsius")
    chief_complaint: str = Field(..., min_length=1, max_length=500, description="Chief complaint text")
    mass_casualty_mode: bool = Field(False, description="Enable mass-casualty routing")
    patient_id: Optional[str] = Field(None, description="Link to existing patient record")
    location: Optional[str] = Field(None, description="ED location/bay for tracking")
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Assessment timestamp")
    
    @validator("chief_complaint")
    def complaint_not_empty(cls, v):
        """Ensure chief complaint is not just whitespace."""
        if not v.strip():
            raise ValueError("Chief complaint cannot be empty")
        return v.strip()
    
    class Config:
        schema_extra = {
            "example": {
                "age": 60,
                "heart_rate": 135,
                "spO2": 90,
                "temperature": 37.2,
                "chief_complaint": "Severe chest pain radiating to left arm, feels crushing",
                "mass_casualty_mode": False,
            }
        }


class BatchTriageRequest(BaseModel):
    """Batch triage assessment request (multiple patients)."""
    
    patients: List[TriageAssessmentRequest] = Field(..., description="List of patients to assess")
    batch_id: Optional[str] = Field(None, description="Batch identifier for tracking")
    priority: Literal["normal", "urgent"] = Field("normal", description="Processing priority")
    
    @validator("patients")
    def non_empty_batch(cls, v):
        """Ensure batch has at least 1 patient."""
        if len(v) < 1:
            raise ValueError("Batch must contain at least 1 patient")
        if len(v) > 10000:
            raise ValueError("Batch size limited to 10,000 patients")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "patients": [
                    {
                        "age": 60,
                        "heart_rate": 135,
                        "spO2": 90,
                        "temperature": 37.2,
                        "chief_complaint": "Chest pain",
                    },
                    {
                        "age": 28,
                        "heart_rate": 76,
                        "spO2": 98,
                        "temperature": 36.8,
                        "chief_complaint": "Twisted ankle",
                    },
                ],
                "batch_id": "batch_2024_001",
            }
        }


class PatientCreate(BaseModel):
    """Create new patient record."""
    
    name: str = Field(..., min_length=2, max_length=100, description="Patient full name")
    age: int = Field(..., ge=1, le=120, description="Patient age")
    medical_record_number: Optional[str] = Field(None, description="MRN (auto-generated if not provided)")
    gender: Optional[Literal["M", "F", "Other"]] = Field(None, description="Gender")
    contact_phone: Optional[str] = Field(None, description="Contact phone number")
    allergies: Optional[str] = Field(None, description="Known allergies (comma-separated)")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "John Doe",
                "age": 45,
                "gender": "M",
                "contact_phone": "+1234567890",
            }
        }


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class ExplainabilityBreakdown(BaseModel):
    """Detailed explainability for triage decision."""
    
    vitals_score: float = Field(..., ge=0, le=1, description="Vital deviations score (0-1)")
    vitals_contribution: float = Field(..., description="Weight contribution to risk")
    
    nlp_urgency: float = Field(..., ge=0, le=1, description="NLP urgency score (0-1)")
    nlp_contribution: float = Field(..., description="Weight contribution to risk")
    nlp_used_fallback: bool = Field(False, description="Whether keyword fallback was used")
    
    age_factor: float = Field(..., ge=0, le=1, description="Age factor score (0-1)")
    age_contribution: float = Field(..., description="Weight contribution to risk")
    
    raw_score: float = Field(..., ge=0, le=1, description="Raw triage risk (0-1)")
    normalized_score: float = Field(..., ge=0, le=1, description="Normalized score for interpretation")
    
    class Config:
        schema_extra = {
            "example": {
                "vitals_score": 0.8,
                "vitals_contribution": 0.4,
                "nlp_urgency": 0.85,
                "nlp_contribution": 0.35,
                "nlp_used_fallback": False,
                "age_factor": 0.6,
                "age_contribution": 0.15,
                "raw_score": 0.78,
                "normalized_score": 0.92,
            }
        }


class TriageAssessmentResponse(BaseModel):
    """Single patient triage assessment response."""
    
    assessment_id: str = Field(..., description="Unique assessment ID")
    patient_id: Optional[str] = Field(None, description="Linked patient ID")
    
    # Vital input confirmation
    age: int = Field(..., description="Patient age (echoed)")
    heart_rate: int = Field(..., description="Heart rate (echoed)")
    spO2: int = Field(..., description="SpO2 (echoed)")
    temperature: float = Field(..., description="Temperature (echoed)")
    chief_complaint: str = Field(..., description="Chief complaint (echoed)")
    
    # Triage result
    esi_level: ESILevel = Field(..., description="Recommended ESI level (1-5)")
    esi_color: ESIColor = Field(..., description="Color badge for UI rendering")
    risk_score: float = Field(..., ge=0, le=1, description="Raw triage risk (0-1)")
    
    # Clinical decision (if any)
    decision: Optional[TriageDecision] = Field(None, description="Auto-triggered decision (null if none)")
    decision_confidence: float = Field(..., ge=0, le=1, description="Confidence in decision (0-1)")
    
    # Explanations
    reason: str = Field(..., description="Plain-English explanation of ESI level")
    decision_rationale: Optional[str] = Field(None, description="Why this decision was triggered")
    
    # Explainability
    explain: ExplainabilityBreakdown = Field(..., description="Detailed breakdown")
    
    # Mode info
    mode: TriageMode = Field("normal", description="Assessment mode used")
    
    # Metadata
    assessment_timestamp: datetime = Field(default_factory=datetime.utcnow)
    latency_ms: float = Field(..., ge=0, description="Processing latency in milliseconds")
    model_version: str = Field(..., description="Model version used")
    
    class Config:
        schema_extra = {
            "example": {
                "assessment_id": "assess_2024_001_abc123",
                "esi_level": 2,
                "esi_color": "red",
                "decision": "auto_order_ecg_cardiac_panel",
                "decision_confidence": 0.94,
                "reason": "Severe chest pain with abnormal vitals (HR 135, SpO2 90%) indicates cardiac emergency.",
                "explain": {
                    "vitals_score": 0.8,
                    "vitals_contribution": 0.4,
                    "nlp_urgency": 0.85,
                    "nlp_contribution": 0.35,
                    "age_factor": 0.6,
                    "age_contribution": 0.15,
                },
                "latency_ms": 87.3,
            }
        }


class BatchTriageResponse(BaseModel):
    """Batch triage processing response."""
    
    batch_id: str = Field(..., description="Batch identifier")
    total_patients: int = Field(..., ge=0, description="Total patients in batch")
    successful: int = Field(..., ge=0, description="Successfully assessed")
    failed: int = Field(..., ge=0, description="Failed assessments")
    
    results: List[TriageAssessmentResponse] = Field(..., description="Individual assessment results")
    errors: List[Dict] = Field(default_factory=list, description="Error details for failed patients")
    
    total_latency_ms: float = Field(..., ge=0, description="Total processing time")
    avg_latency_per_patient_ms: float = Field(..., ge=0, description="Average per patient")
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        schema_extra = {
            "example": {
                "batch_id": "batch_2024_001",
                "total_patients": 2,
                "successful": 2,
                "failed": 0,
                "results": [
                    {
                        "esi_level": 2,
                        "esi_color": "red",
                    },
                    {
                        "esi_level": 5,
                        "esi_color": "blue",
                    },
                ],
                "total_latency_ms": 156.8,
            }
        }


class PatientResponse(BaseModel):
    """Patient record response."""
    
    id: str = Field(..., description="Patient ID")
    name: str = Field(..., description="Patient name")
    age: int = Field(..., description="Patient age")
    medical_record_number: Optional[str] = Field(None, description="MRN")
    gender: Optional[str] = Field(None, description="Gender")
    contact_phone: Optional[str] = Field(None, description="Contact phone")
    allergies: Optional[str] = Field(None, description="Known allergies")
    
    # Triage history
    triage_history: List[TriageAssessmentResponse] = Field(default_factory=list, description="Past assessments")
    last_assessment: Optional[datetime] = Field(None, description="Most recent assessment timestamp")
    
    # Metadata
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


class MetricsSummary(BaseModel):
    """Metrics summary response."""
    
    total_assessments: int = Field(..., ge=0, description="Total triage assessments")
    successful_assessments: int = Field(..., ge=0, description="Successfully completed")
    failed_assessments: int = Field(..., ge=0, description="Failed assessments")
    
    avg_latency_ms: float = Field(..., ge=0, description="Average response time")
    p50_latency_ms: float = Field(..., ge=0, description="Median response time")
    p95_latency_ms: float = Field(..., ge=0, description="95th percentile latency")
    p99_latency_ms: float = Field(..., ge=0, description="99th percentile latency")
    
    # ESI distribution
    esi_distribution: Dict[int, int] = Field(..., description="Count by ESI level")
    
    # Decision triggers
    decision_triggers: Dict[str, int] = Field(default_factory=dict, description="Count by decision type")
    
    # NLP metrics
    nlp_fallback_rate: float = Field(..., ge=0, le=1, description="Percentage using keyword fallback")
    
    # Time period
    time_period_hours: int = Field(..., ge=1, description="Metrics aggregation period")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        schema_extra = {
            "example": {
                "total_assessments": 1250,
                "avg_latency_ms": 87.5,
                "esi_distribution": {1: 45, 2: 180, 3: 520, 4: 380, 5: 125},
                "nlp_fallback_rate": 0.08,
                "time_period_hours": 24,
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response."""
    
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Machine-readable error code")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        schema_extra = {
            "example": {
                "detail": "Invalid heart rate value",
                "error_code": "VALIDATION_ERROR",
            }
        }
