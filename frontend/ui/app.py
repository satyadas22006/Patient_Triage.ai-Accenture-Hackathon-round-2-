"""
frontend/ui/app.py - FIXED VERSION WITH CORRECT IMPORTS

This version has the import path fixes to work with the project structure.
Copy this entire file and replace your current frontend/ui/app.py
"""

# ============================================================================
# IMPORT FIX - ADD THIS AT THE VERY TOP (BEFORE ANY OTHER IMPORTS)
# ============================================================================

import sys
from pathlib import Path

# Add project root to Python path so it can find engine and models
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# ============================================================================
# NOW IMPORT THE REST
# ============================================================================

import streamlit as st
from datetime import datetime

# NOW these imports will work!
from engine.orchestrator import TriageError, run_triage
from models.schemas import PatientInput, TriageResult

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="PatientTriage.ai",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================================
# DARK MODE STYLING
# ============================================================================

st.markdown("""
<style>
.stApp {
    background-color: #0E1117;
    color: #E6E6E6;
}
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
}
.panel-header {
    font-size: 1.05rem;
    font-weight: 700;
    color: #FFFFFF;
    background: linear-gradient(90deg, #6E00B8, #A100FF);
    padding: 10px 14px;
    border-radius: 8px;
    margin-bottom: 14px;
}
.panel-card {
    background-color: #161B22;
    border: 1px solid #262C36;
    border-radius: 10px;
    padding: 16px;
    min-height: 480px;
}
.esi-badge {
    text-align: center;
    padding: 24px;
    border-radius: 10px;
    font-size: 2.8rem;
    font-weight: 800;
    color: #FFFFFF;
}
.esi1 { background-color: #D32F2F; }
.esi2 { background-color: #F57C00; }
.esi3 { background-color: #FBC02D; color: #333333; }
.esi4 { background-color: #7CB342; }
.esi5 { background-color: #1976D2; }
.mcm-banner {
    background-color: #4A0E0E;
    border: 1px solid #C0392B;
    color: #FFD9D9;
    padding: 8px 12px;
    border-radius: 6px;
    font-weight: 600;
    font-size: 0.85rem;
    margin-bottom: 12px;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# ============================================================================
# HEADER
# ============================================================================

st.markdown(
    "<h1 style='margin-bottom:0;'>🩺 PatientTriage.ai</h1>"
    "<p style='color:#8B93A1;margin-top:2px;'>"
    "Multi-Modal Triage Graph (MMTG) — ED Decision Support"
    "</p>",
    unsafe_allow_html=True,
)
st.divider()

# ============================================================================
# THREE-COLUMN LAYOUT
# ============================================================================

left, center, right = st.columns([1, 1.2, 1], gap="medium")

# ---- LEFT: INPUT PANEL ---- #
with left:
    st.markdown('<div class="panel-header">Patient Input</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)

    mass_casualty_mode = st.toggle(
        "Mass Casualty Mode",
        value=False,
        help="Bypasses NLP model for deterministic vitals-only routing",
    )
    
    if mass_casualty_mode:
        st.markdown(
            '<div class="mcm-banner">⚠ MASS CASUALTY MODE — AI Model Bypassed</div>',
            unsafe_allow_html=True,
        )

    st.markdown("**Vitals**")
    age = st.slider("Age (years)", min_value=0, max_value=120, value=45)
    heart_rate = st.slider("Heart Rate (bpm)", min_value=0, max_value=220, value=80)
    spo2 = st.slider("SpO2 (%)", min_value=50.0, max_value=100.0, value=97.0, step=0.5)
    temperature = st.slider(
        "Temperature (°C)", min_value=30.0, max_value=42.0, value=37.0, step=0.1
    )

    st.markdown("**Chief Complaint**")
    chief_complaint = st.text_area(
        "What is the patient's main complaint?",
        placeholder="e.g., 'Severe chest pain radiating to left arm'",
        height=100,
        label_visibility="collapsed",
    )

    submitted = st.button("Run Triage Assessment", type="primary", use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ---- CENTER: RECOMMENDATION PANEL ---- #
with center:
    st.markdown(
        '<div class="panel-header">Recommendation &amp; Actions</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)

    if submitted:
        try:
            # Validate input
            if not chief_complaint.strip():
                st.error("Please enter a chief complaint")
            else:
                # Create patient input
                patient = PatientInput(
                    age=age,
                    heart_rate=heart_rate,
                    spo2=spo2,
                    temperature=temperature,
                    chief_complaint=chief_complaint,
                    mass_casualty_mode=mass_casualty_mode,
                )

                # Run triage
                result, meta = run_triage(patient)

                # Display ESI badge
                esi_css = f"esi{result.esi_level}"
                st.markdown(
                    f'<div class="esi-badge {esi_css}">ESI {result.esi_level}</div>',
                    unsafe_allow_html=True,
                )

                # Display metrics
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Risk Score", f"{result.risk_score:.2f}")
                with col2:
                    st.metric("Latency", f"{meta.latency_ms:.1f}ms")

                # Display decisions
                if result.decisions:
                    st.markdown("**Auto-Triggered Decisions**")
                    for decision in result.decisions:
                        st.success(f"✓ {decision}")
                else:
                    st.info("No auto-triggered decisions")

        except ValueError as e:
            st.error(f"Validation Error: {str(e)}")
        except TriageError as e:
            st.error(f"Triage Error: {str(e)}")
        except Exception as e:
            st.error(f"Unexpected Error: {str(e)}")
    else:
        st.info("Enter patient data and click 'Run Triage Assessment' to see results")

    st.markdown("</div>", unsafe_allow_html=True)

# ---- RIGHT: EXPLAINABILITY PANEL ---- #
with right:
    st.markdown(
        '<div class="panel-header">Explainability</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)

    if submitted and 'result' in locals() and result.explain:
        e = result.explain
        
        st.write(f"**α = {e.alpha}** | **β = {e.beta}** | **γ = {e.gamma}**")

        st.metric("Vital Contribution", f"{e.alpha_contribution:.3f}")
        st.progress(min(1.0, e.alpha_contribution))

        st.metric("NLP Contribution", f"{e.beta_contribution:.3f}")
        st.progress(min(1.0, e.beta_contribution))

        st.metric("Age Contribution", f"{e.gamma_contribution:.3f}")
        st.progress(min(1.0, e.gamma_contribution))

    elif submitted and 'result' in locals() and result.mass_casualty_mode:
        st.info(
            "**Mass Casualty Mode:** Rule-based routing (no AI weighting). "
            "No explainability breakdown provided."
        )
    else:
        st.info("Explainability data will appear here after assessment")

    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.markdown(
    "<p style='text-align: center; color: #8B93A1; font-size: 0.8rem;'>"
    f"PatientTriage.ai • Built {datetime.now().year} • "
    "<a href='#' style='color: #8B93A1;'>Documentation</a>"
    "</p>",
    unsafe_allow_html=True,
)