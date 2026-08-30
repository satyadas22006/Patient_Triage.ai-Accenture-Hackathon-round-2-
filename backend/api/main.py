"""
backend/api/main.py

FastAPI application entry point for PatientTriage.ai backend.
Handles triage assessment requests, patient management, and metrics.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZIPMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
import logging

from database import SessionLocal, engine, Base
from schemas import (
    TriageAssessmentRequest,
    TriageAssessmentResponse,
    PatientCreate,
    PatientResponse,
    BatchTriageRequest,
    BatchTriageResponse,
)
from services import TriageService, PatientService
from middleware.logging_middleware import LoggingMiddleware
from middleware.auth_middleware import verify_api_key
from config import settings

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================================
# LIFESPAN MANAGEMENT
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: Create database tables, initialize services.
    Shutdown: Clean up resources.
    """
    # Startup
    logger.info("Starting up PatientTriage.ai backend...")
    Base.metadata.create_all(bind=engine)
    logger.info("✓ Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down PatientTriage.ai backend...")
    logger.info("✓ All resources cleaned up")


# ============================================================================
# APP INITIALIZATION
# ============================================================================

app = FastAPI(
    title="PatientTriage.ai API",
    version="2.0.0",
    description="AI-powered emergency department triage assessment system",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(GZIPMiddleware, minimum_size=1000)
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

def get_db():
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_triage_service(db=Depends(get_db)) -> TriageService:
    """Get TriageService instance."""
    return TriageService(db)


def get_patient_service(db=Depends(get_db)) -> PatientService:
    """Get PatientService instance."""
    return PatientService(db)


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Simple health check endpoint.
    Returns: {"status": "healthy", "timestamp": "2024-01-01T12:00:00Z"}
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "2.0.0",
    }


@app.get("/health/detailed", tags=["Health"])
async def health_check_detailed(db=Depends(get_db)):
    """
    Detailed health check including database connectivity.
    """
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "2.0.0",
        "components": {
            "api": "up",
            "database": db_status,
            "nlp_model": "ready",  # TODO: Add actual NLP model health check
        },
    }


# ============================================================================
# TRIAGE ENDPOINTS
# ============================================================================

@app.post(
    "/v1/triage/assess",
    response_model=TriageAssessmentResponse,
    tags=["Triage"],
    summary="Perform single-patient triage assessment",
)
async def perform_triage(
    request: TriageAssessmentRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key),
    triage_service: TriageService = Depends(get_triage_service),
):
    """
    Perform a triage assessment on a single patient.
    
    **Parameters:**
    - `age`: Patient age in years (1-120)
    - `heart_rate`: HR in bpm (30-250)
    - `spO2`: SpO2 in % (50-100)
    - `temperature`: Temp in °C (35-42)
    - `chief_complaint`: Chief complaint text (can be very brief)
    - `mass_casualty_mode`: Toggle mass-casualty deterministic routing (optional)
    
    **Returns:**
    - `esi_level`: Recommended ESI level (1-5)
    - `esi_color`: Color badge (red/orange/yellow/green/blue)
    - `decision`: Auto-trigger if any (null if none)
    - `reason`: Plain-English explanation
    - `explain`: Explainability breakdown (vitals, NLP, age)
    - `risk_score`: Raw triage risk (0-1)
    
    **Example:**
    ```json
    {
        "age": 60,
        "heart_rate": 135,
        "spO2": 90,
        "temperature": 37.2,
        "chief_complaint": "Severe chest pain radiating to left arm",
        "mass_casualty_mode": false
    }
    ```
    """
    try:
        logger.info(f"Triage request: age={request.age}, complaint={request.chief_complaint[:30]}...")
        
        # Perform assessment
        result = await triage_service.assess_patient(request)
        
        # Log metrics asynchronously
        background_tasks.add_task(
            triage_service.log_assessment_metrics,
            result,
        )
        
        logger.info(f"✓ Assessment complete: ESI {result.esi_level}")
        return result
        
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Triage assessment failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Assessment failed")


@app.post(
    "/v1/triage/batch",
    response_model=BatchTriageResponse,
    tags=["Triage"],
    summary="Batch triage processing (CSV upload)",
)
async def batch_triage(
    request: BatchTriageRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key),
    triage_service: TriageService = Depends(get_triage_service),
):
    """
    Process multiple patients in a batch from CSV.
    
    **Expected CSV Columns:**
    - age, heart_rate, spO2, temperature, chief_complaint
    
    **Returns:**
    - `total_patients`: Number processed
    - `successful`: Number with successful assessments
    - `failed`: Number with errors
    - `results`: List of individual assessments
    - `timestamp`: Batch processing time
    """
    try:
        logger.info(f"Batch triage request: {len(request.patients)} patients")
        
        result = await triage_service.assess_batch(request.patients)
        
        # Log batch metrics
        background_tasks.add_task(
            triage_service.log_batch_metrics,
            result,
        )
        
        logger.info(f"✓ Batch complete: {result.successful} successful, {result.failed} failed")
        return result
        
    except Exception as e:
        logger.error(f"Batch triage failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Batch processing failed")


# ============================================================================
# PATIENT ENDPOINTS
# ============================================================================

@app.post(
    "/v1/patients",
    response_model=PatientResponse,
    tags=["Patients"],
    status_code=201,
    summary="Create new patient record",
)
async def create_patient(
    request: PatientCreate,
    api_key: str = Depends(verify_api_key),
    patient_service: PatientService = Depends(get_patient_service),
):
    """
    Create a new patient record in the system.
    
    **Parameters:**
    - `name`: Patient name
    - `age`: Patient age
    - `medical_record_number`: MRN (optional, system generates if not provided)
    
    **Returns:**
    - Created patient record with ID
    """
    try:
        logger.info(f"Creating patient: {request.name}")
        patient = await patient_service.create_patient(request)
        logger.info(f"✓ Patient created: ID={patient.id}")
        return patient
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Patient creation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Patient creation failed")


@app.get(
    "/v1/patients/{patient_id}",
    response_model=PatientResponse,
    tags=["Patients"],
    summary="Get patient by ID",
)
async def get_patient(
    patient_id: str,
    api_key: str = Depends(verify_api_key),
    patient_service: PatientService = Depends(get_patient_service),
):
    """Retrieve patient record and triage history."""
    try:
        patient = await patient_service.get_patient(patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        return patient
    except Exception as e:
        logger.error(f"Patient retrieval failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Patient retrieval failed")


@app.get(
    "/v1/patients",
    response_model=List[PatientResponse],
    tags=["Patients"],
    summary="List all patients",
)
async def list_patients(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    api_key: str = Depends(verify_api_key),
    patient_service: PatientService = Depends(get_patient_service),
):
    """
    List all patients with pagination.
    
    **Query Parameters:**
    - `skip`: Number of records to skip (default: 0)
    - `limit`: Number of records to return (default: 100, max: 1000)
    """
    try:
        patients = await patient_service.list_patients(skip=skip, limit=limit)
        return patients
    except Exception as e:
        logger.error(f"Patient listing failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Patient listing failed")


# ============================================================================
# METRICS ENDPOINTS
# ============================================================================

@app.get(
    "/v1/metrics/summary",
    tags=["Metrics"],
    summary="Get triage metrics summary",
)
async def get_metrics_summary(
    hours: int = Query(24, ge=1, le=720),
    api_key: str = Depends(verify_api_key),
    triage_service: TriageService = Depends(get_triage_service),
):
    """
    Get summary metrics for the last N hours.
    
    **Returns:**
    - `total_assessments`: Total count
    - `avg_latency_ms`: Average response time
    - `esi_distribution`: Count by ESI level
    - `decision_triggers`: Count by decision type
    - `nlp_fallback_rate`: Percentage using keyword fallback
    """
    try:
        metrics = await triage_service.get_metrics_summary(hours=hours)
        return metrics
    except Exception as e:
        logger.error(f"Metrics retrieval failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Metrics retrieval failed")


@app.get(
    "/v1/metrics/export",
    tags=["Metrics"],
    summary="Export metrics as JSON/CSV",
)
async def export_metrics(
    format: str = Query("json", regex="^(json|csv)$"),
    api_key: str = Depends(verify_api_key),
    triage_service: TriageService = Depends(get_triage_service),
):
    """
    Export detailed metrics in JSON or CSV format.
    
    **Query Parameters:**
    - `format`: Output format ("json" or "csv")
    
    **Returns:**
    - Metrics file download
    """
    try:
        file_content = await triage_service.export_metrics(format=format)
        
        if format == "csv":
            return {
                "data": file_content,
                "type": "text/csv",
                "filename": f"triage_metrics_{datetime.utcnow().isoformat()}.csv",
            }
        else:
            return file_content
            
    except Exception as e:
        logger.error(f"Metrics export failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Metrics export failed")


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle validation errors."""
    logger.warning(f"Validation error: {str(exc)}")
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected errors."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ============================================================================
# STARTUP / SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """On application startup."""
    logger.info("PatientTriage.ai API starting up...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")


@app.on_event("shutdown")
async def shutdown_event():
    """On application shutdown."""
    logger.info("PatientTriage.ai API shutting down...")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
