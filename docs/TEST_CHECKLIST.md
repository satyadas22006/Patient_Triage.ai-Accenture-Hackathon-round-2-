# PatientTriage.ai — Pre-Submission Test Checklist

Run every scenario below through the live app before submitting. For each:
confirm the ESI badge color/level looks defensible, check whether the
expected decision fires, and glance at the explainability panel for
anything nonsensical (e.g. a contribution that's negative, or wildly out
of proportion to the raw score next to it).

Tick each box as you go. If anything looks wrong, check `engine/orchestrator.py`
first — that's where normal-mode and mass-casualty-mode routing both live.

## Normal Mode

- [ ] **1. Low risk, routine.** Age 28, HR 76, SpO2 98%, Temp 36.8°C,
  complaint: *"Twisted my ankle playing football, it's a bit swollen."*
  Expect: ESI 4–5, no decisions.

- [ ] **2. Classic cardiac emergency.** Age 60, HR 135, SpO2 90%, Temp 37.2°C,
  complaint: *"Severe chest pain radiating to left arm, feels crushing."*
  Expect: ESI 1–2, "Auto-order ECG + Cardiac Enzyme Panel" decision fires.

- [ ] **3. Respiratory distress.** Age 45, HR 110, SpO2 88%, Temp 38.9°C,
  complaint: *"Can't catch my breath, wheezing badly, chest feels tight."*
  Expect: ESI 1–2, pulse-oximetry/oxygen-prep decision fires.

- [ ] **4. Trauma, high vital deviation.** Age 34, HR 145, SpO2 91%, Temp 36.5°C,
  complaint: *"Fell off a ladder, leg looks badly broken, lots of bleeding."*
  Expect: ESI 1–2, trauma-bay routing decision fires.

- [ ] **5. Mid-severity, ambiguous complaint.** Age 50, HR 98, SpO2 95%, Temp 37.9°C,
  complaint: *"Not feeling well, some stomach pain since this morning."*
  Expect: ESI 3, no decision (nothing here should be confident enough to
  auto-trigger anything — this is exactly the kind of case that should
  stay a pure recommendation).

- [ ] **6. Elderly, borderline vitals.** Age 82, HR 92, SpO2 94%, Temp 37.0°C,
  complaint: *"Feeling dizzy and weak since yesterday."*
  Expect: ESI shifted more urgent than a similar case in a younger adult,
  due to the age factor — confirm the explainability panel actually shows
  a visible age contribution.

- [ ] **7. Infant, high fever.** Age 1, HR 160, SpO2 96%, Temp 39.8°C,
  complaint: *"Baby has had a very high fever since last night, very fussy."*
  Expect: elevated ESI driven by age factor + temperature deviation, even
  though SpO2/HR alone might look only moderately abnormal for an infant.

- [ ] **8. Empty/near-empty chief complaint.** Age 40, HR 80, SpO2 97%,
  Temp 37.0°C, complaint: *"pain"* (single word). Confirm the app does
  **not** crash — either it classifies with low confidence or the fallback
  keyword classifier kicks in. Should not silently produce ESI 1.

## Mass Casualty Mode

- [ ] **9. Mass casualty, clearly critical.** Toggle Mass Casualty Mode ON.
  Age 70, HR 140, SpO2 82%, Temp 38.5°C (complaint text irrelevant — it
  must not be read). Expect: ESI 1–2, `explain` panel shows the "not
  applicable, rule-based" message (not a blank/broken panel), `reason`
  field populated with a plain-English explanation.

- [ ] **10. Mass casualty, clearly stable.** Same mode. Age 25, HR 78,
  SpO2 98%, Temp 36.9°C. Expect: ESI 4–5, reason should say something
  like "vitals within or near normal range."

## Cross-cutting checks (do these once, not per-scenario)

- [ ] Toggling Mass Casualty Mode **after** an assessment already ran
  re-routes live using the same vitals, without needing to click
  "Run Triage Assessment" again.
- [ ] Switching Mass Casualty Mode back OFF correctly restores the full
  NLP + risk-engine pipeline (not stuck showing a stale mass-casualty
  result).
- [ ] Submitting with an out-of-range value (e.g. drag SpO2 slider — should
  be impossible via slider, but double check malformed input generally
  can't crash the app) shows a clean validation error, not a traceback.
- [ ] Run `pytest tests/ -v` one final time right before submitting — all
  tests should pass, including `test_decide_trigger_never_contradicts_esi_recommendation`.
