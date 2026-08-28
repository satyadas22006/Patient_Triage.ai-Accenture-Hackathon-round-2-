# PatientTriage.ai — Multi-Modal Triage Graph (MMTG)

AI-powered decision-support prototype for ED triage — built for the Accenture
Innovation Challenge 2026, Round 2.

> Helps hospital staff prioritize patients using only first-minute data (vitals + a
> spoken chief complaint), without replacing clinical judgment.

## Status
✅ End-to-end prototype working — normal mode (NLP + risk DAG) and Mass
Casualty Mode (deterministic vitals-only queue) are both wired up and
tested. See `docs/TEST_CHECKLIST.md` before submitting any further changes.

## Repo structure

```
patienttriage-ai/
├── models/               # Pydantic schemas — the shared data contract
│   └── schemas.py
├── engine/                # MMTG logic
│   ├── nlp_classifier.py       # Zero-shot NLP urgency classifier (+ keyword fallback)
│   ├── risk_engine.py          # RiskDAG — weighted risk score, ESI mapping, decide-triggers
│   ├── vitals_age.py           # Vital deviation + age factor scoring
│   ├── mass_casualty.py        # Deterministic vitals-only bypass queue
│   └── orchestrator.py         # Single entry point — routes normal vs. mass-casualty
├── ui/
│   └── app.py             # Streamlit app — the only place engine functions get called from
├── tests/                  # pytest unit + integration tests
├── docs/
│   ├── TEST_CHECKLIST.md  # Manual QA pass — run before every submission
│   └── DEMO_SHOTLIST.md   # Shot list for the pitch video
├── requirements.txt
└── README.md
```

## How to run

Requires Python 3.10+.

```bash
git clone <your-repo-url>
cd patienttriage-ai

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

streamlit run ui/app.py
```

The app opens at `http://localhost:8501`. First run will download the
`facebook/bart-large-mnli` model (a few hundred MB) — if that's slow or
offline, the app automatically falls back to a keyword-based classifier
so the demo never hard-crashes (you'll see a small banner when that
happens).

**Run the test suite** before every submission:

```bash
pytest tests/ -v
```

All 8 tests should pass. See `docs/TEST_CHECKLIST.md` for the manual
scenario pass to run on top of the automated tests.

## Architecture

The MMTG scores every patient as:

```
Risk = α(Vital_Deviations) + β(NLP_Urgency) + γ(Age_Factor)
```

which maps to a recommended Emergency Severity Index (ESI) level, 1 (most urgent)
to 5 (least urgent). A separate **Mass Casualty Mode** bypasses the NLP model
entirely and ranks patients through a deterministic, vitals-only queue when the
system needs to degrade safely under surge conditions.

If a decide-trigger fires (e.g. a high-confidence cardiac pattern), the
recommended ESI level is never allowed to be weaker than "Emergent" —
the decide and recommend layers are not permitted to contradict each
other. See `DECIDE_TRIGGER_ESI_CEILING` in `engine/orchestrator.py`.

## Team

| Area | Owner |
|---|---|
| Backend, integration, UI, deployment | Satya |
| NLP classifier, risk engine | Qudsia |
| Vitals/age scoring, Mass Casualty Mode, explainability | Ayush |
