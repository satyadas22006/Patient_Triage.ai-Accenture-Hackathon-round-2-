# PatientTriage.ai Round 2 - File Integration Guide

## Complete File Mapping

### Backend Files

**`backend/api/main.py`** - FastAPI application entry point
- Single patient triage endpoint: `POST /v1/triage/assess`
- Batch processing endpoint: `POST /v1/triage/batch`
- Patient management: `POST/GET /v1/patients`
- Metrics endpoints: `GET /v1/metrics/summary`, `GET /v1/metrics/export`
- Health checks: `GET /health`, `GET /health/detailed`
- CORS, logging, error handling middleware

**`backend/config/settings.py`** - Configuration management
- Database URL configuration
- API settings (host, port, debug mode)
- CORS allowed origins
- Authentication settings
- Logging configuration
- Environment-based config loading

**`backend/db/models.py`** - SQLAlchemy ORM models
- `Patient` model with medical record tracking
- `TriageAssessment` model with full audit trail
- `BatchJob` model for tracking batch processing
- `Metric` model for analytics storage
- Relationships and indexes for query optimization

**`backend/schemas/schemas.py`** - Pydantic request/response models
- `TriageAssessmentRequest` - Input validation
- `TriageAssessmentResponse` - Output with ESI level, decision, explainability
- `PatientCreate`, `PatientResponse` - Patient CRUD
- `BatchTriageRequest`, `BatchTriageResponse` - Batch operations
- `MetricsSummary` - Analytics data structure

**`backend/services/triage_service.py`** - Business logic layer
- `TriageService` class integrating the triage engine
- `assess_patient()` - Single patient assessment
- `assess_batch()` - Batch processing with error recovery
- Metrics logging and retrieval
- Integration with SQLAlchemy for persistence

### ML Files

**`ml/training/train.py`** - ML training pipeline
- Custom NLP model fine-tuning
- Dataset preparation for medical urgency classification
- Model evaluation and validation
- Hyperparameter optimization
- Model versioning and checkpointing

### DevOps Files

**`devops/docker/Dockerfile`** - Backend container image
- Python 3.11 base image
- Dependencies installation
- Application setup and startup command

**`devops/docker/docker-compose.dev.yml`** - Local development setup
- PostgreSQL database service
- FastAPI backend service
- Streamlit frontend service
- Volume mounts for code hot-reload
- Network configuration

**`devops/github_actions_ci_cd.yml`** - Automated testing and deployment
- Lint and format checking
- Unit and integration tests
- Docker image building and pushing
- Deployment automation

### Frontend Files

**`frontend/ui/app.py`** - Main Streamlit interface (Round 1)
**`frontend/ui/app_advanced.py`** - Advanced features (batch, metrics)

### Core Engine (Round 1)

**`engine/`** - MMTG triage logic
- `orchestrator.py` - Main entry point
- `risk_engine.py` - Risk scoring DAG
- `nlp_classifier.py` - NLP urgency scoring
- `vitals_age.py` - Vital and age factor scoring
- `mass_casualty.py` - Deterministic fallback
- `config.py`, `metrics.py` - Configuration and observability

**`models/schemas.py`** - Shared Pydantic models

### Configuration Files

**.env.example** - Environment variables template
**requirements.txt** - All Python dependencies
**.gitignore** - Git ignore rules

### Documentation

**docs/SETUP_GUIDE.md** - Complete installation guide
**docs/ROUND2_IMPLEMENTATION_SUMMARY.md** - What's been built
**docs/ROUND2_ROADMAP.md** - Development roadmap
**docs/README_ORIGINAL.md** - Round 1 documentation

---

## Installation & Running

### 1. Backend API
```bash
cd backend
pip install -r ../requirements.txt
export DATABASE_URL=postgresql://user:pass@localhost:5432/patienttriage
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend (Streamlit)
```bash
cd frontend
streamlit run ui/app.py --server.port 8501
```

### 3. Database (Docker)
```bash
docker-compose -f devops/docker/docker-compose.dev.yml up postgres
```

### 4. Full Stack (Docker Compose)
```bash
docker-compose -f devops/docker/docker-compose.dev.yml up
```

---

## API Endpoints

### Triage
- `POST /v1/triage/assess` - Single patient assessment
- `POST /v1/triage/batch` - Batch CSV processing

### Patients
- `POST /v1/patients` - Create patient record
- `GET /v1/patients/{id}` - Get patient details
- `GET /v1/patients` - List all patients

### Metrics
- `GET /v1/metrics/summary` - Summary statistics
- `GET /v1/metrics/export` - Export as JSON/CSV

### Health
- `GET /health` - Simple health check
- `GET /health/detailed` - Detailed component status

---

## Testing

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# Coverage report
pytest tests/ --cov=backend --cov=engine --cov-report=html
```

---

## Deployment

### Docker Compose (Local Development)
```bash
docker-compose -f devops/docker/docker-compose.dev.yml up
```

### Kubernetes (Production)
```bash
# Build image
docker build -f devops/docker/Dockerfile -t patienttriage:latest .

# Push to registry
docker tag patienttriage:latest myregistry.azurecr.io/patienttriage:latest
docker push myregistry.azurecr.io/patienttriage:latest

# Deploy
kubectl apply -f devops/kubernetes/deployment.yaml
```

---

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Database
DATABASE_URL=postgresql://localhost:5432/patienttriage

# API
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True

# NLP
NLP_MODEL=facebook/bart-large-mnli
NLP_DEVICE=cpu  # or 'cuda'

# CORS
CORS_ORIGINS=["http://localhost:3000","http://localhost:8501"]
```

---

## Troubleshooting

### Database Connection Error
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Or install locally
brew install postgresql
brew services start postgresql
```

### Port Already in Use
```bash
# Backend
python -m uvicorn api.main:app --port 8001

# Frontend
streamlit run ui/app.py --server.port 8502
```

### NLP Model Download Error
```bash
# Pre-download model
python -c "from transformers import pipeline; pipeline('zero-shot-classification', model='facebook/bart-large-mnli')"
```

---

## Next Steps

1. Follow `docs/SETUP_GUIDE.md` for complete setup
2. Review `docs/ROUND2_ROADMAP.md` for development priorities
3. Read `docs/ROUND2_IMPLEMENTATION_SUMMARY.md` to understand what's built
4. Start with the Streamlit frontend for testing
5. Use the API for integration with external systems

