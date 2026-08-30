# 🩺 PatientTriage.ai

### Explainable AI-Assisted Emergency Department Triage

PatientTriage.ai is an AI-assisted emergency department triage decision-support prototype designed to help prioritize patients using information available during the first minutes of an emergency-department assessment.

The system combines:

- 🧠 Natural-language urgency classification
- ❤️ Vital-sign deviation analysis
- 👤 Age-based risk adjustment
- 🕸️ An explicit Explainable Risk DAG
- 🚨 Narrow, high-confidence decision triggers
- ⚡ Deterministic Mass Casualty Mode
- 🔍 Per-patient explainability
- 📊 Latency and triage metrics
- 🧪 Synthetic patient scenarios and automated tests
- 🌐 Streamlit demonstration UI
- 🔌 FastAPI/PostgreSQL backend architecture
- 🐳 Docker and CI/CD scaffolding

> **Medical safety notice**
>
> PatientTriage.ai is a research, educational and hackathon prototype.
> It is not a medical device, does not provide autonomous medical diagnosis,
> and must not replace qualified clinical judgment, validated emergency
> protocols, or professional medical care.

---

# ✨ Why PatientTriage.ai?

Emergency departments need to make decisions quickly, often with incomplete information.

A useful AI-assisted triage system should not only answer:

> **"How urgent is this patient?"**

It should also answer:

> **"Why did the system reach that recommendation?"**

And in a smaller number of carefully defined situations:

> **"Is there a narrow, high-confidence action that should be surfaced immediately?"**

PatientTriage.ai separates these two responsibilities.

```text
                 PATIENT
                    │
                    ▼
             TRIAGE ENGINE
                    │
          ┌─────────┴─────────┐
          │                   │
          ▼                   ▼
   RECOMMENDATION          DECISION
          │                   │
       ESI 1–5          Narrow protocol action
          │                   │
          └─────────┬─────────┘
                    ▼
             CLINICAL REVIEW