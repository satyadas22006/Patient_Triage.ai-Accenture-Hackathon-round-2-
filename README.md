# PatientTriage.ai - Round 2 Complete

Full-stack AI-powered emergency triage system with:
- **Backend**: FastAPI with PostgreSQL
- **Frontend**: Streamlit web interface
- **ML**: Custom NLP model training and deployment
- **DevOps**: Docker, Docker Compose, GitHub Actions CI/CD

## Quick Start

See `docs/SETUP_GUIDE.md` for complete installation instructions.

```bash
# Backend
cd backend
python -m uvicorn api.main:app --reload

# Frontend  
cd frontend
streamlit run ui/app.py

# ML Training
python ml/training/train.py
```

## Directory Structure

```
patienttriage-ai-round2-complete/
├── backend/                    # FastAPI application
│   ├── api/main.py            # Main API endpoints
│   ├── services/              # Business logic
│   ├── db/                     # Database models
│   ├── schemas/               # Pydantic schemas
│   ├── config/                # Configuration
│   └── middleware/            # Auth, logging, etc
├── frontend/                   # Streamlit UI
│   └── ui/                    # App components
├── ml/                         # Machine learning
│   ├── training/              # Model training pipeline
│   └── models/                # Trained model files
├── engine/                     # Core triage logic (from Round 1)
├── models/                     # Data models
├── tests/                      # Test suites
├── devops/                     # Deployment configs
│   ├── docker/                # Docker files
│   └── kubernetes/            # K8s configs
├── docs/                       # Documentation
└── requirements.txt            # Python dependencies
```

## Documentation

- `docs/SETUP_GUIDE.md` - Installation and setup
- `docs/ROUND2_ROADMAP.md` - Development roadmap
- `docs/ROUND2_IMPLEMENTATION_SUMMARY.md` - What's been built
- `docs/README_ORIGINAL.md` - Original Round 1 documentation

## Features

✅ Single patient triage assessment
✅ Batch processing (CSV upload)
✅ Patient record management
✅ Detailed metrics and analytics
✅ Auto-decision triggers for critical cases
✅ Mass casualty mode (deterministic fallback)
✅ Live explainability dashboard
✅ API documentation (Swagger/OpenAPI)
✅ Production-ready with error handling
✅ CI/CD with GitHub Actions

## Running Tests

```bash
# All tests
pytest tests/

# With coverage
pytest tests/ --cov=backend --cov=engine
```

## Deployment

See `devops/docker/docker-compose.dev.yml` and `Dockerfile` for containerized deployment.

```bash
docker-compose -f devops/docker/docker-compose.dev.yml up
```

