# PatientTriage.ai Round 2 - Complete Setup & Deployment Guide

## 🚀 Quick Start (5 minutes)

### Prerequisites
- Python 3.11+
- PostgreSQL 13+
- Docker & Docker Compose (optional, for containerized setup)
- Git

### Local Development Setup

```bash
# 1. Clone repository
git clone <your-repo-url>
cd patienttriage-ai

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements_round2.txt

# 4. Set up environment
cp .env.example .env
# Edit .env with your local database credentials

# 5. Initialize database
alembic upgrade head

# 6. Start FastAPI server
uvicorn backend.api.main:app --reload --port 8000

# 7. In another terminal, start Streamlit UI
streamlit run ui/app.py

# 8. Access applications
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - Streamlit UI: http://localhost:8501
```

---

## 🐳 Docker Setup (Recommended for Development)

### Using Docker Compose

```bash
# 1. Start all services
docker-compose -f docker-compose.dev.yml up -d

# 2. Check service status
docker-compose -f docker-compose.dev.yml ps

# 3. Access services
# - API: http://localhost:8000
# - Streamlit: http://localhost:8501
# - PostgreSQL: localhost:5432
# - MLflow: http://localhost:5000
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000

# 4. View logs
docker-compose -f docker-compose.dev.yml logs -f api

# 5. Stop services
docker-compose -f docker-compose.dev.yml down
```

### Manual Docker Build

```bash
# Build backend image
docker build -f Dockerfile.backend -t patienttriage-api:latest .

# Run with database
docker run -d \
  --name patienttriage-api \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@postgres:5432/db \
  --link postgres:postgres \
  patienttriage-api:latest
```

---

## 📚 Project Structure

```
patienttriage-ai/
├── backend/                    # ✨ NEW - FastAPI backend
│   ├── api/
│   │   ├── main.py            # Main FastAPI application
│   │   ├── routes/            # API endpoint definitions
│   │   ├── middleware/        # Authentication, logging
│   │   └── dependencies.py    # Dependency injection
│   ├── db/
│   │   ├── models.py          # SQLAlchemy ORM models
│   │   ├── schemas.py         # Pydantic schemas
│   │   └── database.py        # Database connection
│   ├── services/
│   │   ├── triage_service.py  # Triage business logic
│   │   └── patient_service.py # Patient management
│   ├── config.py              # Configuration management
│   └── __init__.py
│
├── ml/                        # ✨ NEW - Machine Learning
│   ├── training/
│   │   ├── train.py          # Training pipeline
│   │   ├── datasets.py       # Data loading
│   │   └── evaluate.py       # Model evaluation
│   ├── models/
│   │   ├── nlp_model.py      # Custom NLP model
│   │   └── weights/          # Model checkpoints
│   ├── inference/
│   │   └── inference.py      # Model serving
│   └── mlflow/
│       └── MLproject         # Experiment config
│
├── engine/                    # ✓ EXISTING - Triage logic
│   ├── orchestrator_v2.py
│   ├── risk_engine.py
│   ├── nlp_classifier.py
│   ├── mass_casualty.py
│   ├── metrics.py
│   └── config.py
│
├── ui/                        # ✓ EXISTING - Streamlit UI
│   ├── app.py
│   ├── app_advanced.py
│   └── components/
│
├── tests/                     # ✓ EXISTING - Test suite
│   ├── test_engine.py
│   ├── test_integration_advanced.py
│   └── synthetic_patients.py
│
├── docker/                    # ✨ NEW - Container configs
│   ├── Dockerfile.backend
│   ├── Dockerfile.ml
│   ├── docker-compose.dev.yml
│   └── init-db.sql
│
├── k8s/                       # ✨ NEW - Kubernetes
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml
│   └── secrets.yaml
│
├── docs/                      # ✨ EXPANDED - Documentation
│   ├── API_REFERENCE.md
│   ├── MODEL_CARD.md
│   ├── DEPLOYMENT.md
│   └── CONTRIBUTING.md
│
├── .github/workflows/         # ✨ NEW - CI/CD
│   └── ci-cd.yml
│
├── requirements_round2.txt    # All dependencies
├── .env.example              # Environment template
├── README.md
└── ROUND2_ROADMAP.md
```

---

## 🗄️ Database Setup

### PostgreSQL Installation

```bash
# macOS
brew install postgresql
brew services start postgresql

# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql

# Windows
# Download from https://www.postgresql.org/download/windows/
```

### Initialize Database

```bash
# Create database and user
createdb patienttriage_ai
psql -d patienttriage_ai -c "CREATE USER patienttriage_user WITH PASSWORD 'secure_password';"
psql -d patienttriage_ai -c "GRANT ALL PRIVILEGES ON DATABASE patienttriage_ai TO patienttriage_user;"

# Run migrations
alembic upgrade head

# Verify setup
psql -d patienttriage_ai -c "\dt"  # List tables
```

---

## 🤖 ML Model Training

### Quick Start Training

```bash
# 1. Prepare data (uses built-in medical urgency corpus)
python ml/training/train.py

# 2. Track experiment with MLflow
mlflow ui --backend-store-uri file:./mlruns

# 3. Evaluate model
python ml/training/evaluate.py

# 4. Export for serving
python ml/inference/export_model.py \
  --checkpoint models/checkpoints/final_model \
  --output models/serving/medical_urgency_model
```

### Advanced Training with Custom Data

```python
from ml.training.train import MedicalTriageModelTrainer, TrainingConfig
from ml.training.datasets import MedicalUrgencyDataset

# Load config
config = TrainingConfig()

# Create dataset with custom examples
custom_data = [
    ("Acute myocardial infarction with ECG changes", 0),
    ("Minor laceration, bleeding controlled", 4),
    # ... more examples
]
dataset = MedicalUrgencyDataset.create_dataset(config, custom_data)

# Train
trainer = MedicalTriageModelTrainer(config)
trainer.setup()
trainer.train(dataset)
trainer.save_model("models/custom_model")
```

---

## 🚢 Deployment

### Local/Staging Deployment

```bash
# Start all services with Docker Compose
docker-compose -f docker-compose.dev.yml up

# Run tests
pytest tests/ -v

# Check API health
curl http://localhost:8000/health
```

### Production Kubernetes Deployment

```bash
# 1. Build Docker image
docker build -f Dockerfile.backend -t patienttriage-api:v2.0.0 .

# 2. Push to registry
docker tag patienttriage-api:v2.0.0 gcr.io/your-project/patienttriage-api:v2.0.0
docker push gcr.io/your-project/patienttriage-api:v2.0.0

# 3. Apply Kubernetes manifests
kubectl apply -f k8s/prod/namespace.yaml
kubectl apply -f k8s/prod/configmap.yaml
kubectl apply -f k8s/prod/secrets.yaml
kubectl apply -f k8s/prod/postgres.yaml
kubectl apply -f k8s/prod/deployment.yaml
kubectl apply -f k8s/prod/service.yaml

# 4. Verify deployment
kubectl get pods -n production
kubectl logs -f deployment/patienttriage-api -n production

# 5. Check service
kubectl get svc patienttriage-api -n production
```

---

## 📊 API Usage Examples

### Single Triage Assessment

```bash
curl -X POST http://localhost:8000/v1/triage/assess \
  -H "Content-Type: application/json" \
  -d '{
    "age": 60,
    "heart_rate": 135,
    "spO2": 90,
    "temperature": 37.2,
    "chief_complaint": "Severe chest pain radiating to left arm"
  }'
```

### Batch Processing

```bash
curl -X POST http://localhost:8000/v1/triage/batch \
  -H "Content-Type: application/json" \
  -d '{
    "patients": [
      {
        "age": 60,
        "heart_rate": 135,
        "spO2": 90,
        "temperature": 37.2,
        "chief_complaint": "Chest pain"
      },
      {
        "age": 28,
        "heart_rate": 76,
        "spO2": 98,
        "temperature": 36.8,
        "chief_complaint": "Twisted ankle"
      }
    ]
  }'
```

### Get Metrics

```bash
curl http://localhost:8000/v1/metrics/summary?hours=24
```

See `docs/API_REFERENCE.md` for complete API documentation.

---

## 🧪 Testing

### Run All Tests

```bash
# Unit tests
pytest tests/test_engine.py -v

# Integration tests
pytest tests/test_integration_advanced.py -v

# With coverage
pytest tests/ --cov=engine --cov=backend --cov-report=html

# Specific test
pytest tests/test_engine.py::test_cardiac_emergency -v
```

### Load Testing

```bash
# Install locust
pip install locust

# Run load tests
locust -f tests/load_test.py --host=http://localhost:8000
```

---

## 🔧 Configuration

### Environment Variables (.env)

```bash
# Application
ENVIRONMENT=production
DEBUG=false

# Database
DB_HOST=postgres.prod.local
DB_PORT=5432
DB_USER=patienttriage_user
DB_PASSWORD=your-secure-password
DB_NAME=patienttriage_ai

# NLP Model
NLP_MODEL_NAME=facebook/bart-large-mnli
NLP_DEVICE=cuda
NLP_TIMEOUT=30.0

# Risk Engine
RISK_ALPHA=0.50
RISK_BETA=0.35
RISK_GAMMA=0.15

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Security
API_KEY_REQUIRED=true
VALID_API_KEYS=key1,key2,key3

# Monitoring
MLFLOW_TRACKING_URI=http://mlflow.prod.local:5000
PROMETHEUS_ENABLED=true
```

---

## 📈 Monitoring & Observability

### MLflow Experiment Tracking

```bash
# Start MLflow server
mlflow server --backend-store-uri postgresql://... --default-artifact-root s3://...

# Track experiments
python ml/training/train.py  # Logs to MLflow automatically

# View dashboard
open http://localhost:5000
```

### Prometheus Metrics

```bash
# Prometheus is automatically exposed at :9090
# Scrape metrics from: http://localhost:8000/metrics
```

### Grafana Dashboards

```bash
# Access Grafana
open http://localhost:3000
# Login with admin/admin
# View dashboards in Grafana/dashboards
```

---

## 🐛 Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
psql -U postgres -d patienttriage_ai -c "SELECT 1;"

# View migration status
alembic current

# Reset database (development only)
alembic downgrade base
alembic upgrade head
```

### NLP Model Loading Issues

```bash
# Check CUDA availability
python -c "import torch; print(torch.cuda.is_available())"

# Force CPU
export NLP_DEVICE=cpu

# Clear cache
rm -rf models/cache/
```

### API Not Responding

```bash
# Check logs
docker-compose logs -f api

# Check port
lsof -i :8000

# Restart service
docker-compose restart api
```

---

## 📋 Checklist for Deployment

- [ ] All tests passing: `pytest tests/ -v`
- [ ] Code quality checks passing: `black --check .`, `flake8 .`
- [ ] Database migrations up to date: `alembic current`
- [ ] Environment variables configured: `.env` file reviewed
- [ ] Docker images built and tested
- [ ] API health check passing: `curl /health`
- [ ] Load test passed: `locust`
- [ ] Documentation updated
- [ ] Monitoring configured (Prometheus, Grafana)
- [ ] Backup strategy in place
- [ ] Rollback plan documented

---

## 📞 Support & Help

- **API Documentation**: http://localhost:8000/docs
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Email**: team@patienttriage.ai

---

## 🎯 Next Steps

1. **This Week**: Get local environment running, run tests
2. **Next Week**: Fine-tune NLP model with medical corpus
3. **Week 3**: Deploy to staging, run smoke tests
4. **Week 4**: Production deployment, monitoring setup

See `ROUND2_ROADMAP.md` for detailed timeline.
