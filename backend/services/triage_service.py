"""
backend/services/triage_service.py

Business logic for triage assessments.
Integrates existing engine with database persistence and metrics logging.
"""

import logging
import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

# Import from existing engine (assumed to be installed)
from engine.orchestrator_v2 import TriageOrchestrator, TriageConfig
from engine.metrics import MetricsCollector

from schemas import (
    TriageAssessmentRequest,
    TriageAssessmentResponse,
    ExplainabilityBreakdown,
    ESIColor,
    TriageDecision,
    TriageMode,
    BatchTriageResponse,
    MetricsSummary,
)
from db.models import (
    TriageAssessment,
    Patient,
    AuditLog,
    MetricsLog,
    BatchJob,
    ESILevelEnum,
    TriageModeEnum,
)

logger = logging.getLogger(__name__)


# ============================================================================
# TRIAGE SERVICE
# ============================================================================

class TriageService:
    """Business logic for triage assessments."""
    
    def __init__(self, db: Session):
        self.db = db
        
        # Initialize triage orchestrator
        self.config = TriageConfig()
        self.orchestrator = TriageOrchestrator(self.config)
        self.metrics_collector = MetricsCollector()
        
        logger.info(f"TriageService initialized: model={self.config.nlp_model_name}")
    
    # ========================================================================
    # SINGLE PATIENT ASSESSMENT
    # ========================================================================
    
    async def assess_patient(
        self,
        request: TriageAssessmentRequest,
    ) -> TriageAssessmentResponse:
        """
        Perform triage assessment on a single patient.
        
        Flow:
        1. Validate input
        2. Run through orchestrator
        3. Map result to response schema
        4. Save to database
        5. Return response
        
        Args:
            request: Triage assessment request
            
        Returns:
            TriageAssessmentResponse with ESI level and decision
            
        Raises:
            ValueError: If input validation fails
        """
        start_time = time.time()
        
        try:
            # Validate input
            self._validate_input(request)
            
            # Run triage (existing engine logic)
            orchestrator_result = await asyncio.to_thread(
                self.orchestrator.assess_patient,
                age=request.age,
                heart_rate=request.heart_rate,
                spO2=request.spO2,
                temperature=request.temperature,
                chief_complaint=request.chief_complaint,
                mass_casualty_mode=request.mass_casualty_mode,
            )
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            # Map to response schema
            response = self._map_to_response(
                request=request,
                result=orchestrator_result,
                latency_ms=latency_ms,
            )
            
            # Save to database
            assessment_record = self._save_assessment(request, response, orchestrator_result)
            
            # Log audit trail
            self._log_audit("assessment_created", assessment_record.id, {
                "esi_level": response.esi_level,
                "decision": response.decision,
            })
            
            # Record metrics
            self.metrics_collector.log_assessment(
                latency_ms=latency_ms,
                esi_level=response.esi_level,
                nlp_fallback_used=orchestrator_result.get("nlp_fallback", False),
            )
            
            logger.info(f"✓ Assessment complete: {response.assessment_id} ESI-{response.esi_level}")
            return response
            
        except ValueError as e:
            logger.warning(f"Validation error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Assessment failed: {str(e)}", exc_info=True)
            raise
    
    # ========================================================================
    # BATCH PROCESSING
    # ========================================================================
    
    async def assess_batch(
        self,
        patients: List[TriageAssessmentRequest],
    ) -> BatchTriageResponse:
        """
        Process multiple patients in a batch.
        
        Args:
            patients: List of assessment requests
            
        Returns:
            BatchTriageResponse with individual results
        """
        batch_start = time.time()
        batch_id = f"batch_{datetime.utcnow().isoformat()}"
        
        # Create batch job record
        batch_job = BatchJob(
            batch_id=batch_id,
            total_patients=len(patients),
            status="processing",
            started_at=datetime.utcnow(),
        )
        self.db.add(batch_job)
        self.db.commit()
        
        results = []
        errors = []
        successful = 0
        failed = 0
        
        # Process each patient
        for idx, patient_request in enumerate(patients, 1):
            try:
                logger.info(f"Batch {batch_id}: Processing {idx}/{len(patients)}...")
                result = await self.assess_patient(patient_request)
                results.append(result)
                successful += 1
            except Exception as e:
                logger.warning(f"Batch patient {idx} failed: {str(e)}")
                errors.append({
                    "patient_index": idx,
                    "error": str(e),
                    "chief_complaint": patient_request.chief_complaint[:50],
                })
                failed += 1
        
        # Calculate timings
        total_latency_ms = (time.time() - batch_start) * 1000
        avg_latency_per_patient = total_latency_ms / len(patients) if patients else 0
        
        # Update batch job
        batch_job.status = "completed"
        batch_job.successful = successful
        batch_job.failed = failed
        batch_job.total_latency_ms = total_latency_ms
        batch_job.avg_latency_per_patient_ms = avg_latency_per_patient
        batch_job.completed_at = datetime.utcnow()
        batch_job.results_summary = {
            "esi_distribution": self._get_esi_distribution(results),
            "decision_triggers": self._get_decision_triggers(results),
        }
        if errors:
            batch_job.errors = errors
        
        self.db.commit()
        
        # Create response
        response = BatchTriageResponse(
            batch_id=batch_id,
            total_patients=len(patients),
            successful=successful,
            failed=failed,
            results=results,
            errors=errors,
            total_latency_ms=total_latency_ms,
            avg_latency_per_patient_ms=avg_latency_per_patient,
        )
        
        logger.info(f"✓ Batch complete: {batch_id} - {successful} successful, {failed} failed")
        return response
    
    # ========================================================================
    # METRICS & ANALYTICS
    # ========================================================================
    
    async def get_metrics_summary(self, hours: int = 24) -> MetricsSummary:
        """
        Get metrics summary for the specified time period.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            MetricsSummary with aggregated metrics
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Query assessments from this period
        assessments = self.db.query(TriageAssessment).filter(
            TriageAssessment.created_at >= cutoff_time
        ).all()
        
        if not assessments:
            return MetricsSummary(
                total_assessments=0,
                successful_assessments=0,
                failed_assessments=0,
                avg_latency_ms=0,
                p50_latency_ms=0,
                p95_latency_ms=0,
                p99_latency_ms=0,
                esi_distribution={i: 0 for i in range(1, 6)},
                decision_triggers={},
                nlp_fallback_rate=0.0,
                time_period_hours=hours,
            )
        
        # Calculate metrics
        latencies = [a.latency_ms for a in assessments]
        latencies_sorted = sorted(latencies)
        
        def percentile(data, p):
            n = len(data)
            i = int(n * p / 100)
            return data[i] if i < n else data[-1]
        
        # ESI distribution
        esi_dist = {}
        for i in range(1, 6):
            count = sum(1 for a in assessments if a.esi_level == ESILevelEnum(i))
            esi_dist[i] = count
        
        # Decision triggers
        decision_counts = {}
        for a in assessments:
            if a.decision:
                decision_counts[a.decision] = decision_counts.get(a.decision, 0) + 1
        
        # NLP fallback rate
        fallback_count = sum(1 for a in assessments if a.nlp_fallback_used)
        nlp_fallback_rate = fallback_count / len(assessments) if assessments else 0
        
        return MetricsSummary(
            total_assessments=len(assessments),
            successful_assessments=len(assessments),
            failed_assessments=0,
            avg_latency_ms=sum(latencies) / len(latencies),
            p50_latency_ms=percentile(latencies_sorted, 50),
            p95_latency_ms=percentile(latencies_sorted, 95),
            p99_latency_ms=percentile(latencies_sorted, 99),
            esi_distribution=esi_dist,
            decision_triggers=decision_counts,
            nlp_fallback_rate=nlp_fallback_rate,
            time_period_hours=hours,
        )
    
    async def export_metrics(self, format: str = "json") -> Dict[str, Any]:
        """
        Export detailed metrics.
        
        Args:
            format: Export format ("json" or "csv")
            
        Returns:
            Metrics data in requested format
        """
        assessments = self.db.query(TriageAssessment).all()
        
        if format == "csv":
            # Generate CSV content
            import csv
            from io import StringIO
            
            output = StringIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow([
                "assessment_id", "patient_id", "age", "heart_rate", "spO2",
                "temperature", "esi_level", "risk_score", "latency_ms",
                "decision", "nlp_fallback", "timestamp"
            ])
            
            # Rows
            for a in assessments:
                writer.writerow([
                    a.id, a.patient_id, a.age, a.heart_rate, a.spO2,
                    a.temperature, int(a.esi_level), a.risk_score, a.latency_ms,
                    a.decision, a.nlp_fallback_used, a.created_at.isoformat()
                ])
            
            return output.getvalue()
        else:
            # JSON format
            return {
                "total_assessments": len(assessments),
                "assessments": [
                    {
                        "id": a.id,
                        "patient_id": a.patient_id,
                        "esi_level": int(a.esi_level),
                        "risk_score": a.risk_score,
                        "latency_ms": a.latency_ms,
                        "decision": a.decision,
                        "timestamp": a.created_at.isoformat(),
                    }
                    for a in assessments
                ]
            }
    
    async def log_assessment_metrics(self, result: TriageAssessmentResponse):
        """Log metrics for a completed assessment (background task)."""
        try:
            metrics = MetricsLog(
                latency_ms=result.latency_ms,
                nlp_fallback_used=result.explain.nlp_used_fallback,
                esi_level=int(result.esi_level),
                risk_score=result.risk_score,
                heart_rate=result.heart_rate,
                spO2=result.spO2,
                temperature=result.temperature,
                mode=result.mode.value,
                model_version=result.model_version,
            )
            self.db.add(metrics)
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to log metrics: {str(e)}")
    
    async def log_batch_metrics(self, result: BatchTriageResponse):
        """Log summary metrics for a batch job (background task)."""
        # Already logged in assess_batch, but can add additional processing here
        pass
    
    # ========================================================================
    # PRIVATE HELPERS
    # ========================================================================
    
    def _validate_input(self, request: TriageAssessmentRequest) -> None:
        """Validate triage input."""
        if not 1 <= request.age <= 120:
            raise ValueError(f"Invalid age: {request.age}")
        if not 30 <= request.heart_rate <= 250:
            raise ValueError(f"Invalid heart rate: {request.heart_rate}")
        if not 50 <= request.spO2 <= 100:
            raise ValueError(f"Invalid SpO2: {request.spO2}")
        if not 35 <= request.temperature <= 42:
            raise ValueError(f"Invalid temperature: {request.temperature}")
        if not request.chief_complaint or not request.chief_complaint.strip():
            raise ValueError("Chief complaint cannot be empty")
    
    def _map_to_response(
        self,
        request: TriageAssessmentRequest,
        result: Dict[str, Any],
        latency_ms: float,
    ) -> TriageAssessmentResponse:
        """Map orchestrator result to response schema."""
        
        esi_level = result.get("esi_level", 3)
        esi_color_map = {1: ESIColor.RED, 2: ESIColor.ORANGE, 3: ESIColor.YELLOW, 4: ESIColor.GREEN, 5: ESIColor.BLUE}
        
        decision_str = result.get("decision")
        decision = None
        if decision_str and decision_str != "none":
            try:
                decision = TriageDecision(decision_str)
            except ValueError:
                decision = None
        
        explain = result.get("explain", {})
        
        return TriageAssessmentResponse(
            assessment_id=result.get("assessment_id", f"assess_{datetime.utcnow().isoformat()}"),
            patient_id=request.patient_id,
            age=request.age,
            heart_rate=request.heart_rate,
            spO2=request.spO2,
            temperature=request.temperature,
            chief_complaint=request.chief_complaint,
            esi_level=esi_level,
            esi_color=esi_color_map.get(esi_level, ESIColor.YELLOW),
            risk_score=result.get("risk_score", 0.5),
            decision=decision,
            decision_confidence=result.get("decision_confidence", 0.0),
            reason=result.get("reason", f"ESI-{esi_level} recommended."),
            decision_rationale=result.get("decision_rationale"),
            explain=ExplainabilityBreakdown(
                vitals_score=explain.get("vitals_score", 0.0),
                vitals_contribution=explain.get("vitals_contribution", 0.0),
                nlp_urgency=explain.get("nlp_urgency", 0.0),
                nlp_contribution=explain.get("nlp_contribution", 0.0),
                nlp_used_fallback=explain.get("nlp_used_fallback", False),
                age_factor=explain.get("age_factor", 0.0),
                age_contribution=explain.get("age_contribution", 0.0),
                raw_score=explain.get("raw_score", 0.0),
                normalized_score=explain.get("normalized_score", 0.0),
            ),
            mode=TriageMode.MASS_CASUALTY if request.mass_casualty_mode else TriageMode.NORMAL,
            latency_ms=latency_ms,
            model_version=self.config.nlp_model_name,
        )
    
    def _save_assessment(
        self,
        request: TriageAssessmentRequest,
        response: TriageAssessmentResponse,
        result: Dict[str, Any],
    ) -> TriageAssessment:
        """Save assessment to database."""
        assessment = TriageAssessment(
            patient_id=request.patient_id or self._get_or_create_patient(request),
            age=request.age,
            heart_rate=request.heart_rate,
            spO2=request.spO2,
            temperature=request.temperature,
            chief_complaint=request.chief_complaint,
            esi_level=ESILevelEnum(response.esi_level),
            esi_color=response.esi_color.value,
            risk_score=response.risk_score,
            decision=response.decision.value if response.decision else None,
            decision_confidence=response.decision_confidence,
            decision_rationale=response.decision_rationale,
            reason=response.reason,
            explain=response.explain.dict(),
            mode=TriageModeEnum.MASS_CASUALTY if request.mass_casualty_mode else TriageModeEnum.NORMAL,
            latency_ms=response.latency_ms,
            model_version=response.model_version,
            nlp_fallback_used=response.explain.nlp_used_fallback,
            ed_location=request.location,
            assessment_timestamp=request.timestamp or datetime.utcnow(),
        )
        self.db.add(assessment)
        self.db.commit()
        return assessment
    
    def _get_or_create_patient(self, request: TriageAssessmentRequest) -> str:
        """Get or create patient record for anonymous assessments."""
        patient = Patient(
            name=f"Anonymous_{datetime.utcnow().isoformat()}",
            age=request.age,
        )
        self.db.add(patient)
        self.db.commit()
        return patient.id
    
    def _log_audit(self, event_type: str, assessment_id: str, details: Dict):
        """Log audit trail."""
        audit = AuditLog(
            assessment_id=assessment_id,
            event_type=event_type,
            details=details,
        )
        self.db.add(audit)
        self.db.commit()
    
    def _get_esi_distribution(self, results: List[TriageAssessmentResponse]) -> Dict[int, int]:
        """Get ESI level distribution from results."""
        dist = {i: 0 for i in range(1, 6)}
        for r in results:
            dist[int(r.esi_level)] += 1
        return dist
    
    def _get_decision_triggers(self, results: List[TriageAssessmentResponse]) -> Dict[str, int]:
        """Get decision trigger counts from results."""
        triggers = {}
        for r in results:
            if r.decision:
                triggers[r.decision.value] = triggers.get(r.decision.value, 0) + 1
        return triggers
