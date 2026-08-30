# PatientTriage.ai Round 2 - Development Roadmap

## 🎯 Phase Priority: Model Training & Backend First

### Phase 1: Model Training & Optimization (WEEKS 1-2)
**Goal**: Improve NLP classifier accuracy, add custom training, baseline metrics

#### 1.1 Custom NLP Model Training
- [ ] Dataset curation for medical urgency classification
- [ ] Fine-tune BART on custom triage corpus
- [ ] Implement LoRA/QLoRA for efficient training
- [ ] A/B test multiple model architectures (DistilBERT, MedBERT, custom)
- [ ] Generate model comparison report

#### 1.2 Risk Engine Tuning
- [ ] Analyze current weight distributions (α, β, γ)
- [ ] Implement Bayesian optimization for weight tuning
- [ ] Create calibration curves for age/vitals scoring
- [ ] Validate against baseline datasets

#### 1.3 Metrics & Monitoring
- [ ] Set up MLflow for model tracking
- [ ] Create baseline performance dashboard
- [ ] Implement A/B testing framework
- [ ] Document model versioning strategy

---

### Phase 2: Backend Completion (WEEKS 2-4)
**Goal**: Production-ready API, database, error handling, deployment config

#### 2.1 Backend API Development
- [ ] FastAPI/Flask REST endpoints
- [ ] Input validation & sanitization
- [ ] Error recovery & retry logic
- [ ] Rate limiting & caching
- [ ] API documentation (OpenAPI/Swagger)

#### 2.2 Database Integration
- [ ] PostgreSQL schema design
- [ ] Patient history tracking
- [ ] Audit logging for compliance
- [ ] Connection pooling & optimization

#### 2.3 Production Hardening
- [ ] Containerization (Docker/Kubernetes)
- [ ] Environment configuration
- [ ] Secrets management
- [ ] Health checks & monitoring
- [ ] Logging & observability (ELK stack)

#### 2.4 CI/CD Pipeline
- [ ] GitHub Actions workflow
- [ ] Automated testing on push
- [ ] Pre-commit hooks
- [ ] Staging & prod deployment gates

---

### Phase 3: Frontend (WEEKS 5-6)
**Goal**: Polish UI, add batch processing, dashboards

#### 3.1 Core UI Improvements
- [ ] Redesign vitals input interface
- [ ] Implement real-time validation
- [ ] Add patient history view
- [ ] Create printable triage cards

#### 3.2 Advanced Features
- [ ] Batch CSV processing
- [ ] Metrics dashboard
- [ ] Export/archive functionality
- [ ] Mobile-responsive design

---

## 📊 Success Metrics for Round 2

| Metric | Target | Status |
|--------|--------|--------|
| NLP Model F1 Score | >0.92 | To start |
| API Latency (p99) | <200ms | To build |
| Test Coverage | >90% | In progress |
| Deployment Time | <5min | To implement |
| Database Query Time | <50ms | To optimize |

---

## 🚀 Immediate Actions (This Sprint)

1. **Set up MLOps pipeline** → Start model training
2. **Build FastAPI skeleton** → Core endpoints
3. **Create PostgreSQL schema** → Data persistence
4. **Add comprehensive logging** → Debug visibility
5. **Implement CI/CD** → Automate deployment

---

## 📁 Project Structure (Round 2)

```
patienttriage-ai/
├── backend/                     # NEW: Backend API & services
│   ├── api/
│   │   ├── main.py             # FastAPI app
│   │   ├── routes/
│   │   │   ├── triage.py        # Triage endpoints
│   │   │   ├── patients.py      # Patient CRUD
│   │   │   └── metrics.py       # Metrics endpoints
│   │   └── middleware/
│   │       ├── auth.py
│   │       └── logging.py
│   ├── db/
│   │   ├── models.py            # SQLAlchemy ORM
│   │   ├── schemas.py           # Pydantic schemas
│   │   └── migrations/          # Alembic migrations
│   ├── services/
│   │   ├── triage_service.py    # Business logic
│   │   └── patient_service.py   # CRUD operations
│   └── config.py                # Backend config
├── ml/                          # NEW: ML models & training
│   ├── training/
│   │   ├── train.py             # Training pipeline
│   │   ├── datasets.py          # Data loading
│   │   └── metrics.py           # Evaluation
│   ├── models/
│   │   ├── nlp_model.py         # Custom NLP model
│   │   └── weights/             # Model checkpoints
│   ├── inference/
│   │   └── inference.py         # Model serving
│   └── mlflow/
│       └── MLproject            # Experiment tracking
├── engine/                      # EXISTING: Triage logic
├── ui/                          # EXISTING: Streamlit app
├── tests/                       # EXISTING + NEW: Tests
├── docker/                      # NEW: Container configs
│   ├── Dockerfile.api
│   ├── Dockerfile.ml
│   └── docker-compose.yml
├── docs/                        # NEW: Expanded docs
│   ├── API_REFERENCE.md
│   ├── MODEL_CARD.md
│   ├── DEPLOYMENT.md
│   └── CONTRIBUTING.md
├── k8s/                         # NEW: Kubernetes manifests
└── .github/workflows/           # NEW: CI/CD pipelines
```

---

## 🔗 Dependencies by Phase

```
Phase 1 (ML Training)
├─ transformers, torch, datasets
├─ mlflow, wandb
└─ optuna (hyperparameter tuning)

Phase 2 (Backend)
├─ fastapi, uvicorn
├─ sqlalchemy, alembic, psycopg2
├─ pydantic
└─ python-dotenv, pydantic-settings

Phase 3 (Frontend)
├─ streamlit
├─ plotly, pandas
└─ (already mostly in requirements.txt)
```

---

## 📝 Next Steps
1. Review this roadmap with team
2. Create feature branches for each phase
3. Set up MLflow tracking server
4. Begin Phase 1.1 (Dataset curation)
