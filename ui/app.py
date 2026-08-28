"""
ui/app.py

PatientTriage.ai — fully wired Streamlit app.

Run with:
    streamlit run ui/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running as `streamlit run ui/app.py` from repo root without a package install.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from pydantic import ValidationError

from engine.orchestrator import TriageError, run_triage
from models.schemas import PatientInput, TriageResult

# --------------------------------------------------------------------------- #
# Page config — must be the first Streamlit call
# --------------------------------------------------------------------------- #

st.set_page_config(
    page_title="PatientTriage.ai",
    page_icon="\U0001FA7A",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --------------------------------------------------------------------------- #
# Dark-mode styling
# --------------------------------------------------------------------------- #

st.markdown(
    """
    <style>
    .stApp { background-color: #0E1117; color: #E6E6E6; }
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    .panel-header {
        font-size: 1.05rem; font-weight: 700; color: #FFFFFF;
        background: linear-gradient(90deg, #6E00B8, #A100FF);
        padding: 10px 14px; border-radius: 8px; margin-bottom: 14px;
    }
    .panel-card {
        background-color: #161B22; border: 1px solid #262C36;
        border-radius: 10px; padding: 16px; min-height: 480px;
    }
    .placeholder-text { color: #8B93A1; font-size: 0.92rem; line-height: 1.5; margin-top: 8px; }
    .mcm-banner {
        background-color: #4A0E0E; border: 1px solid #C0392B; color: #FFD9D9;
        padding: 8px 12px; border-radius: 6px; font-weight: 600;
        font-size: 0.85rem; margin-bottom: 12px; text-align: center;
    }
    .fallback-banner {
        background-color: #4A3B0E; border: 1px solid #C09B2B; color: #FFF0D9;
        padding: 6px 10px; border-radius: 6px; font-size: 0.78rem;
        margin-bottom: 12px; text-align: center;
    }
    .esi-badge {
        text-align: center; padding: 22px 10px; border-radius: 10px;
        font-size: 2.4rem; font-weight: 800; color: #FFFFFF; margin-bottom: 10px;
    }
    .esi-sub { text-align: center; font-size: 0.85rem; color: #C8C8C8; margin-bottom: 16px; }
    .decision-item {
        background-color: #1F1500; border-left: 4px solid #E0A100; color: #FFE9B3;
        padding: 8px 12px; border-radius: 4px; margin-bottom: 8px; font-size: 0.9rem;
    }
    .no-decision {
        color: #6FCF97; font-size: 0.9rem; padding: 6px 0;
    }
    .reason-box {
        background-color: #0E1117; border: 1px solid #262C36; border-radius: 6px;
        padding: 10px 12px; font-size: 0.85rem; color: #C8C8C8; margin-top: 10px;
    }
    div[data-testid="stTextArea"] textarea { background-color: #0E1117; color: #E6E6E6; }
    </style>
    """,
    unsafe_allow_html=True,
)

ESI_COLORS = {
    1: "#D32F2F",  # red
    2: "#F57C00",  # orange
    3: "#FBC02D",  # yellow
    4: "#7CB342",  # green
    5: "#1976D2",  # blue
}
ESI_LABELS = {
    1: "Resuscitation",
    2: "Emergent",
    3: "Urgent",
    4: "Less Urgent",
    5: "Non-Urgent",
}

# --------------------------------------------------------------------------- #
# Session state — persists the last result across reruns (e.g. toggling
# Mass Casualty Mode after a run should re-route live without needing a
# fresh click of "Run Triage Assessment").
# --------------------------------------------------------------------------- #

st.session_state.setdefault("last_result", None)
st.session_state.setdefault("last_meta", None)
st.session_state.setdefault("last_inputs", None)   # dict of raw widget values
st.session_state.setdefault("last_mode", None)
st.session_state.setdefault("last_error", None)


def _compute(raw: dict) -> None:
    """Build a PatientInput from raw widget values, run triage, store results."""
    st.session_state["last_error"] = None
    try:
        patient = PatientInput(**raw)
    except ValidationError as exc:
        st.session_state["last_error"] = (
            "Invalid patient data — please check the highlighted fields:\n\n"
            + "\n".join(f"- {e['loc'][0]}: {e['msg']}" for e in exc.errors())
        )
        st.session_state["last_result"] = None
        return

    try:
        result, meta = run_triage(patient)
        st.session_state["last_result"] = result
        st.session_state["last_meta"] = meta
        st.session_state["last_inputs"] = raw
        st.session_state["last_mode"] = raw["mass_casualty_mode"]
    except TriageError as exc:
        st.session_state["last_error"] = f"Triage engine error: {exc}"
        st.session_state["last_result"] = None


# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #

st.markdown(
    "<h1 style='margin-bottom:0;'>\U0001FA7A PatientTriage.ai</h1>"
    "<p style='color:#8B93A1;margin-top:2px;'>"
    "Multi-Modal Triage Graph (MMTG) &middot; ED decision-support prototype"
    "</p>",
    unsafe_allow_html=True,
)
st.divider()

left, center, right = st.columns([1, 1.2, 1], gap="medium")

# ---- LEFT: Input panel ------------------------------------------------- #
with left:
    st.markdown('<div class="panel-header">Patient Input</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)

    mass_casualty_mode = st.toggle(
        "Mass Casualty Mode",
        value=bool(st.session_state["last_mode"]) if st.session_state["last_mode"] is not None else False,
        help="Bypasses the NLP model entirely and routes through the "
        "deterministic vitals-only priority queue.",
    )
    if mass_casualty_mode:
        st.markdown(
            '<div class="mcm-banner">\u26A0 MASS CASUALTY MODE ACTIVE — AI model bypassed</div>',
            unsafe_allow_html=True,
        )

    st.markdown("**Vitals**")
    age = st.slider("Age (years)", min_value=0, max_value=120, value=45)
    heart_rate = st.slider("Heart rate (bpm)", min_value=0, max_value=220, value=80)
    spo2 = st.slider("SpO2 (%)", min_value=50.0, max_value=100.0, value=97.0, step=0.5)
    temperature = st.slider("Temperature (\u00b0C)", min_value=30.0, max_value=42.0, value=37.0, step=0.1)

    st.markdown("**Chief Complaint**")
    chief_complaint = st.text_area(
        "What is the patient's main complaint?",
        placeholder='e.g. "Patient clutching chest, says it feels tight"',
        height=100,
        label_visibility="collapsed",
    )

    submitted = st.button("Run Triage Assessment", type="primary", use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

# --------------------------------------------------------------------------- #
# Decide whether to (re)compute this run:
#   1. Explicit "Run" click, using current widget values.
#   2. Mass Casualty toggle changed since the last computed result, and a
#      result already exists — re-route live using the same vitals/complaint.
# --------------------------------------------------------------------------- #

raw_current = {
    "age": age,
    "heart_rate": heart_rate,
    "spo2": spo2,
    "temperature": temperature,
    "chief_complaint": chief_complaint or "",
    "mass_casualty_mode": mass_casualty_mode,
}

if submitted:
    _compute(raw_current)
elif (
    st.session_state["last_inputs"] is not None
    and st.session_state["last_mode"] is not None
    and st.session_state["last_mode"] != mass_casualty_mode
):
    # Live re-route: reuse the last submitted vitals/complaint, new mode.
    reroute_inputs = dict(st.session_state["last_inputs"])
    reroute_inputs["mass_casualty_mode"] = mass_casualty_mode
    _compute(reroute_inputs)

result: TriageResult | None = st.session_state["last_result"]
meta = st.session_state["last_meta"]
error = st.session_state["last_error"]

# ---- CENTER: Recommendation & Action panel ------------------------------ #
with center:
    st.markdown('<div class="panel-header">Recommendation &amp; Actions</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)

    if error:
        st.error(error)
    elif result is None:
        st.markdown(
            '<p class="placeholder-text">No assessment run yet. '
            "Fill in the patient details on the left and click "
            "<b>Run Triage Assessment</b>.</p>",
            unsafe_allow_html=True,
        )
    else:
        if result.mass_casualty_mode:
            st.markdown(
                '<div class="mcm-banner">\u26A0 Result from Mass Casualty queue '
                "(deterministic, vitals-only — NLP not used)</div>",
                unsafe_allow_html=True,
            )
        elif meta is not None and meta.used_nlp_fallback:
            st.markdown(
                '<div class="fallback-banner">NLP model unavailable — '
                "used keyword-based fallback classifier</div>",
                unsafe_allow_html=True,
            )

        color = ESI_COLORS[result.esi_level]
        st.markdown(
            f'<div class="esi-badge" style="background-color:{color};">'
            f"ESI {result.esi_level}</div>"
            f'<div class="esi-sub">{ESI_LABELS[result.esi_level]} '
            f"&middot; Risk Score {result.risk_score:.2f} "
            f"&middot; <i>Recommended — nurse confirms</i></div>",
            unsafe_allow_html=True,
        )

        st.markdown("**Auto-Triggered Actions**")
        if result.decisions:
            for d in result.decisions:
                st.markdown(f'<div class="decision-item">{d}</div>', unsafe_allow_html=True)
        else:
            st.markdown(
                '<div class="no-decision">No auto-triggered actions for this patient.</div>',
                unsafe_allow_html=True,
            )

        if result.reason:
            st.markdown(f'<div class="reason-box"><b>Why:</b> {result.reason}</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ---- RIGHT: Explainability panel ---------------------------------------- #
with right:
    st.markdown('<div class="panel-header">Explainability</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)

    if error or result is None:
        st.markdown(
            '<p class="placeholder-text">No assessment run yet. Once a result comes '
            "back, this panel will show the live &alpha; / &beta; / &gamma; weight "
            "breakdown behind the risk score.</p>",
            unsafe_allow_html=True,
        )
    elif result.explain is None:
        st.markdown(
            '<p class="placeholder-text">Not applicable — this result came from the '
            "Mass Casualty queue, which is rule-based rather than weighted, so there "
            "is no &alpha;/&beta;/&gamma; breakdown to show.</p>",
            unsafe_allow_html=True,
        )
    else:
        e = result.explain
        st.caption(f"Risk = {e.alpha:.1f}\u00b7Vitals + {e.beta:.1f}\u00b7NLP + {e.gamma:.1f}\u00b7Age")

        st.markdown(f"**Vital Deviation** — raw {e.vital_deviation:.2f}, contributes {e.alpha_contribution:.2f}")
        st.progress(min(1.0, e.alpha_contribution))

        st.markdown(f"**NLP Urgency** — raw {e.nlp_urgency:.2f}, contributes {e.beta_contribution:.2f}")
        st.progress(min(1.0, e.beta_contribution))

        st.markdown(f"**Age Factor** — raw {e.age_factor:.2f}, contributes {e.gamma_contribution:.2f}")
        st.progress(min(1.0, e.gamma_contribution))

    st.markdown("</div>", unsafe_allow_html=True)
