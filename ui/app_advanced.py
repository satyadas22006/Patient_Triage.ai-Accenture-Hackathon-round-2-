"""
ui/app_advanced.py — Advanced Streamlit app with demo mode and better UX
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from pydantic import ValidationError

from engine.orchestrator import TriageError, run_triage
from models.schemas import PatientInput, TriageResult
from tests.synthetic_patients import DEMO_SCENARIOS, get_scenario_by_name

st.set_page_config(page_title="PatientTriage.ai", page_icon="🩺", layout="wide", initial_sidebar_state="collapsed")

st.markdown(
    """
    <style>
    .stApp { background-color: #0E1117; color: #E6E6E6; }
    .panel-header {
        font-size: 1.05rem; font-weight: 700; color: #FFFFFF;
        background: linear-gradient(90deg, #6E00B8, #A100FF);
        padding: 10px 14px; border-radius: 8px; margin-bottom: 14px;
    }
    .panel-card { background-color: #161B22; border: 1px solid #262C36; border-radius: 10px; padding: 16px; }
    .mcm-banner { background-color: #4A0E0E; border: 1px solid #C0392B; color: #FFD9D9; padding: 8px 12px; border-radius: 6px; }
    .esi-badge { text-align: center; padding: 22px 10px; border-radius: 10px; font-size: 2.4rem; font-weight: 800; color: #FFFFFF; }
    .decision-item { background-color: #1F1500; border-left: 4px solid #E0A100; color: #FFE9B3; padding: 8px 12px; border-radius: 4px; margin-bottom: 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

ESI_COLORS = {1: "#D32F2F", 2: "#F57C00", 3: "#FBC02D", 4: "#7CB342", 5: "#1976D2"}
ESI_LABELS = {1: "Resuscitation", 2: "Emergent", 3: "Urgent", 4: "Less Urgent", 5: "Non-Urgent"}

st.session_state.setdefault("last_result", None)
st.session_state.setdefault("last_meta", None)
st.session_state.setdefault("last_inputs", None)
st.session_state.setdefault("last_mode", None)
st.session_state.setdefault("last_error", None)

def _compute(raw: dict) -> None:
    st.session_state["last_error"] = None
    try:
        patient = PatientInput(**raw)
    except ValidationError as exc:
        st.session_state["last_error"] = "Invalid patient data"
        st.session_state["last_result"] = None
        return
    try:
        result, meta = run_triage(patient)
        st.session_state["last_result"] = result
        st.session_state["last_meta"] = meta
        st.session_state["last_inputs"] = raw
        st.session_state["last_mode"] = raw["mass_casualty_mode"]
    except TriageError as exc:
        st.session_state["last_error"] = f"Triage error: {exc}"
        st.session_state["last_result"] = None

st.markdown("<h1>🩺 PatientTriage.ai</h1>", unsafe_allow_html=True)
st.divider()

left, center, right = st.columns([1, 1.2, 1], gap="medium")

with left:
    st.markdown('<div class="panel-header">Patient Input</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    
    mass_casualty_mode = st.toggle("Mass Casualty Mode", value=False)
    if mass_casualty_mode:
        st.markdown('<div class="mcm-banner">⚠ MASS CASUALTY MODE ACTIVE</div>', unsafe_allow_html=True)
    
    age = st.slider("Age (years)", 0, 120, 45)
    heart_rate = st.slider("Heart rate (bpm)", 0, 220, 80)
    spo2 = st.slider("SpO2 (%)", 50.0, 100.0, 97.0, 0.5)
    temperature = st.slider("Temperature (°C)", 30.0, 42.0, 37.0, 0.1)
    
    chief_complaint = st.text_area("Chief Complaint", placeholder='e.g. "Patient clutching chest"', height=100)
    submitted = st.button("Run Triage Assessment", type="primary", use_container_width=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

raw = {"age": age, "heart_rate": heart_rate, "spo2": spo2, "temperature": temperature, "chief_complaint": chief_complaint or "", "mass_casualty_mode": mass_casualty_mode}

if submitted:
    _compute(raw)
elif st.session_state["last_inputs"] and st.session_state["last_mode"] != mass_casualty_mode:
    reroute = dict(st.session_state["last_inputs"])
    reroute["mass_casualty_mode"] = mass_casualty_mode
    _compute(reroute)

result = st.session_state["last_result"]

with center:
    st.markdown('<div class="panel-header">Recommendation</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    
    if st.session_state["last_error"]:
        st.error(st.session_state["last_error"])
    elif result:
        color = ESI_COLORS[result.esi_level]
        st.markdown(f'<div class="esi-badge" style="background-color:{color};">ESI {result.esi_level}</div>', unsafe_allow_html=True)
        st.markdown(f'<p style="text-align:center;">{ESI_LABELS[result.esi_level]} · Risk {result.risk_score:.2f}</p>', unsafe_allow_html=True)
        
        if result.decisions:
            for d in result.decisions:
                st.markdown(f'<div class="decision-item">{d}</div>', unsafe_allow_html=True)
    else:
        st.write("No assessment run yet.")
    
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="panel-header">Explainability</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    
    if result and result.explain:
        e = result.explain
        st.progress(min(1.0, e.alpha_contribution))
        st.progress(min(1.0, e.beta_contribution))
        st.progress(min(1.0, e.gamma_contribution))
    else:
        st.write("Waiting for assessment...")
    
    st.markdown("</div>", unsafe_allow_html=True)
