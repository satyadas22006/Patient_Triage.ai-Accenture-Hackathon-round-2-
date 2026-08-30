"""
ui/app.py

PatientTriage.ai
Explainable AI-assisted emergency triage decision support UI.

Run:
    streamlit run ui/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Project path
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

import streamlit as st
from pydantic import ValidationError

from engine.orchestrator import TriageError, run_triage
from models.schemas import PatientInput, TriageResult


# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="PatientTriage.ai",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ===========================================================================
# CONSTANTS
# ===========================================================================

ESI_COLORS = {
    1: "#D32F2F",
    2: "#F57C00",
    3: "#FBC02D",
    4: "#7CB342",
    5: "#1976D2",
}

ESI_LABELS = {
    1: "Resuscitation",
    2: "Emergent",
    3: "Urgent",
    4: "Less Urgent",
    5: "Non-Urgent",
}

ESI_DESCRIPTIONS = {
    1: "Immediate life-saving intervention required.",
    2: "High-acuity presentation requiring rapid clinical assessment.",
    3: "Urgent evaluation recommended.",
    4: "Less urgent presentation.",
    5: "Non-urgent presentation.",
}


# ===========================================================================
# SESSION STATE
# ===========================================================================

DEFAULT_STATE = {
    "last_result": None,
    "last_meta": None,
    "last_inputs": None,
    "last_mode": False,
    "last_error": None,
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ===========================================================================
# CUSTOM CSS
# ===========================================================================

st.markdown(
    """
    <style>

    /* ---------------------------------------------------------------
       APP
       --------------------------------------------------------------- */

    .stApp {
        background:
            radial-gradient(
                circle at top right,
                rgba(137, 0, 255, 0.08),
                transparent 35%
            ),
            #0B0F14;
        color: #E8ECF1;
    }

    .block-container {
        max-width: 1500px;
        padding-top: 1.2rem;
        padding-bottom: 2rem;
    }

    /* ---------------------------------------------------------------
       HEADER
       --------------------------------------------------------------- */

    .hero {
        padding: 8px 0 4px 0;
    }

    .hero-title {
        font-size: 2.15rem;
        line-height: 1.1;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.5px;
    }

    .hero-subtitle {
        margin-top: 6px;
        color: #9099A8;
        font-size: 0.95rem;
    }

    .hero-note {
        margin-top: 8px;
        display: inline-block;
        padding: 5px 10px;
        border-radius: 999px;
        background: #151B24;
        border: 1px solid #28303B;
        color: #B8C1CF;
        font-size: 0.76rem;
    }

    /* ---------------------------------------------------------------
       SECTION HEADERS
       --------------------------------------------------------------- */

    .section-header {
        background: linear-gradient(
            90deg,
            #7200C9,
            #A100FF
        );
        color: #FFFFFF;
        font-size: 0.98rem;
        font-weight: 750;
        padding: 11px 14px;
        border-radius: 9px;
        margin-bottom: 10px;
        min-height: 44px;
        display: flex;
        align-items: center;
    }

    /* ---------------------------------------------------------------
       CARDS
       --------------------------------------------------------------- */

    .card {
        background: #121820;
        border: 1px solid #252E39;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 10px;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.14);
    }

    .compact-card {
        background: #121820;
        border: 1px solid #252E39;
        border-radius: 12px;
        padding: 13px 15px;
        margin-bottom: 10px;
    }

    /* ---------------------------------------------------------------
       TOP STATUS ROW
       --------------------------------------------------------------- */

    .status-row {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-top: 10px;
        margin-bottom: 18px;
    }

    .status-pill {
        display: inline-flex;
        align-items: center;
        padding: 6px 10px;
        border-radius: 999px;
        background: #111821;
        border: 1px solid #27313D;
        color: #ADB8C6;
        font-size: 0.74rem;
        font-weight: 600;
    }

    .status-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: #6FCF97;
        margin-right: 7px;
    }

    /* ---------------------------------------------------------------
       EMPTY STATE
       --------------------------------------------------------------- */

    .empty-state {
        min-height: 215px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 26px 18px;
        color: #7F8A9A;
    }

    .empty-icon {
        font-size: 2rem;
        margin-bottom: 8px;
        opacity: 0.85;
    }

    .empty-title {
        color: #D9E0E8;
        font-size: 0.98rem;
        font-weight: 700;
        margin-bottom: 5px;
    }

    .empty-copy {
        max-width: 290px;
        color: #7F8A9A;
        font-size: 0.82rem;
        line-height: 1.45;
    }

    /* ---------------------------------------------------------------
       MODE BANNERS
       --------------------------------------------------------------- */

    .mcm-banner {
        background: #341111;
        border: 1px solid #9F3939;
        color: #FFD8D8;
        border-radius: 8px;
        padding: 9px 11px;
        font-size: 0.78rem;
        font-weight: 700;
        margin: 10px 0 12px 0;
        text-align: center;
    }

    .fallback-banner {
        background: #34290D;
        border: 1px solid #8F7422;
        color: #FFE7A5;
        border-radius: 8px;
        padding: 8px 11px;
        font-size: 0.76rem;
        margin-bottom: 12px;
        text-align: center;
    }

    .coherence-banner {
        background: #102A1B;
        border: 1px solid #2A7D52;
        color: #BCEFD4;
        border-radius: 8px;
        padding: 8px 11px;
        font-size: 0.76rem;
        margin-bottom: 12px;
        text-align: center;
    }

    /* ---------------------------------------------------------------
       ESI
       --------------------------------------------------------------- */

    .esi-badge {
        border-radius: 12px;
        padding: 19px 12px;
        text-align: center;
        color: #FFFFFF;
        font-size: 2.65rem;
        font-weight: 850;
        letter-spacing: -1px;
        margin-bottom: 8px;
    }

    .esi-label {
        text-align: center;
        color: #E8ECF1;
        font-size: 0.95rem;
        font-weight: 700;
    }

    .esi-sub {
        text-align: center;
        color: #8E99A8;
        font-size: 0.79rem;
        margin-top: 3px;
        margin-bottom: 15px;
    }

    /* ---------------------------------------------------------------
       ACTIONS
       --------------------------------------------------------------- */

    .action-title {
        font-size: 0.82rem;
        font-weight: 750;
        color: #DDE4EC;
        margin-top: 5px;
        margin-bottom: 7px;
    }

    .decision-item {
        background: #231A06;
        border-left: 4px solid #E2AA18;
        color: #FFE8A7;
        padding: 10px 12px;
        border-radius: 6px;
        margin-bottom: 8px;
        font-size: 0.81rem;
        line-height: 1.4;
    }

    .no-decision {
        background: #0F2119;
        border: 1px solid #1E4D38;
        color: #86D7AE;
        padding: 9px 11px;
        border-radius: 7px;
        font-size: 0.79rem;
    }

    .reason-box {
        margin-top: 10px;
        padding: 10px 11px;
        background: #0D131A;
        border: 1px solid #26313C;
        border-radius: 7px;
        color: #AEB8C4;
        font-size: 0.78rem;
        line-height: 1.45;
    }

    /* ---------------------------------------------------------------
       EXPLAINABILITY
       --------------------------------------------------------------- */

    .formula {
        background: #0D131A;
        border: 1px solid #26313C;
        border-radius: 8px;
        padding: 9px 10px;
        color: #CDD5DF;
        font-size: 0.78rem;
        margin-bottom: 13px;
        text-align: center;
    }

    .factor-label {
        display: flex;
        justify-content: space-between;
        gap: 8px;
        margin-bottom: 3px;
        color: #DDE4EC;
        font-size: 0.79rem;
    }

    .factor-raw {
        color: #818D9D;
    }

    .weight-line {
        color: #7F8A99;
        font-size: 0.70rem;
        margin-bottom: 4px;
    }

    /* ---------------------------------------------------------------
       METRICS
       --------------------------------------------------------------- */

    .metric-box {
        background: #0D131A;
        border: 1px solid #26313C;
        border-radius: 8px;
        padding: 9px 10px;
    }

    .metric-label {
        color: #7E8A99;
        font-size: 0.68rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .metric-value {
        color: #E7EDF4;
        font-size: 1.05rem;
        font-weight: 750;
        margin-top: 2px;
    }

    /* ---------------------------------------------------------------
       INPUTS
       --------------------------------------------------------------- */

    div[data-testid="stSlider"] {
        margin-bottom: 3px;
    }

    div[data-testid="stTextArea"] textarea {
        background: #0D131A !important;
        color: #E8ECF1 !important;
        border: 1px solid #2A3440 !important;
        border-radius: 8px !important;
    }

    /* Make primary button feel like an app control. */
    div.stButton > button[kind="primary"] {
        border-radius: 9px;
        font-weight: 750;
        min-height: 43px;
    }

    /* ---------------------------------------------------------------
       FOOTER
       --------------------------------------------------------------- */

    .footer {
        text-align: center;
        color: #606B79;
        font-size: 0.68rem;
        margin-top: 20px;
        padding-top: 10px;
        border-top: 1px solid #1B222B;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ===========================================================================
# HELPERS
# ===========================================================================

def set_error(message: str) -> None:
    """Clear result state and display an engine error."""
    st.session_state["last_error"] = message
    st.session_state["last_result"] = None
    st.session_state["last_meta"] = None


def compute_triage(raw: dict) -> None:
    """Validate the form data, run the engine, and store the result."""
    st.session_state["last_error"] = None

    try:
        patient = PatientInput(**raw)

    except ValidationError as exc:
        messages = []

        for error in exc.errors():
            location = ".".join(str(x) for x in error["loc"])
            messages.append(
                f"{location}: {error['msg']}"
            )

        set_error(
            "Invalid patient data:\n\n"
            + "\n".join(f"• {message}" for message in messages)
        )
        return

    try:
        result, meta = run_triage(patient)

        st.session_state["last_result"] = result
        st.session_state["last_meta"] = meta
        st.session_state["last_inputs"] = raw
        st.session_state["last_mode"] = raw["mass_casualty_mode"]
        st.session_state["last_error"] = None

    except TriageError as exc:
        set_error(
            f"Triage engine error: {exc}"
        )

    except Exception as exc:
        set_error(
            f"Unexpected error: {exc}"
        )


def render_empty_state(
    icon: str,
    title: str,
    copy: str,
) -> None:
    """Render a compact empty panel."""
    st.markdown(
        f"""
        <div class="empty-state">
            <div class="empty-icon">{icon}</div>
            <div class="empty-title">{title}</div>
            <div class="empty-copy">{copy}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric(
    label: str,
    value: str,
) -> None:
    """Render a compact metric box."""
    st.markdown(
        f"""
        <div class="metric-box">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ===========================================================================
# HEADER
# ===========================================================================

st.markdown(
    """
    <div class="hero">
        <div class="hero-title">🩺 PatientTriage.ai</div>
        <div class="hero-subtitle">
            Multi-Modal Triage Graph (MMTG) · Explainable ED Decision Support
        </div>
        <div class="hero-note">
            AI-assisted recommendation · Human confirmation required
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="status-row">
        <div class="status-pill">
            <span class="status-dot"></span>
            NLP + Vitals + Age
        </div>
        <div class="status-pill">
            <span class="status-dot"></span>
            Explainable Risk DAG
        </div>
        <div class="status-pill">
            <span class="status-dot"></span>
            Decision Triggers
        </div>
        <div class="status-pill">
            <span class="status-dot"></span>
            Mass Casualty Fallback
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ===========================================================================
# THREE-COLUMN LAYOUT
# ===========================================================================

left, center, right = st.columns(
    [1.05, 1.15, 1.05],
    gap="medium",
)


# ===========================================================================
# LEFT: PATIENT INPUT
# ===========================================================================

with left:

    st.markdown(
        '<div class="section-header">Patient Input</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="card">', unsafe_allow_html=True)

    mass_casualty_mode = st.toggle(
        "Mass Casualty Mode",
        value=(
            bool(st.session_state["last_mode"])
            if st.session_state["last_mode"] is not None
            else False
        ),
        help=(
            "Bypasses NLP and uses deterministic "
            "vitals-only routing for surge conditions."
        ),
    )

    if mass_casualty_mode:
        st.markdown(
            """
            <div class="mcm-banner">
                ⚠ MASS CASUALTY MODE ACTIVE · NLP BYPASSED
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="action-title">First-minute vitals</div>',
        unsafe_allow_html=True,
    )

    age = st.slider(
        "Age (years)",
        min_value=0,
        max_value=120,
        value=45,
    )

    heart_rate = st.slider(
        "Heart rate (bpm)",
        min_value=0,
        max_value=220,
        value=80,
    )

    spo2 = st.slider(
        "SpO2 (%)",
        min_value=50.0,
        max_value=100.0,
        value=97.0,
        step=0.5,
    )

    temperature = st.slider(
        "Temperature (°C)",
        min_value=30.0,
        max_value=42.0,
        value=37.0,
        step=0.1,
    )

    st.markdown(
        '<div class="action-title">Chief complaint</div>',
        unsafe_allow_html=True,
    )

    chief_complaint = st.text_area(
        "Chief complaint",
        placeholder=(
            'Example: "Severe chest pain radiating to left arm, feels crushing"'
        ),
        height=115,
        label_visibility="collapsed",
    )

    submitted = st.button(
        "Run Triage Assessment",
        type="primary",
        use_container_width=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)


# ===========================================================================
# COMPUTATION / LIVE MASS-CASUALTY REROUTE
# ===========================================================================

current_inputs = {
    "age": age,
    "heart_rate": heart_rate,
    "spo2": spo2,
    "temperature": temperature,
    "chief_complaint": chief_complaint or "",
    "mass_casualty_mode": mass_casualty_mode,
}

if submitted:

    compute_triage(current_inputs)

elif (
    st.session_state["last_inputs"] is not None
    and st.session_state["last_mode"] is not None
    and st.session_state["last_mode"] != mass_casualty_mode
):

    reroute_inputs = dict(
        st.session_state["last_inputs"]
    )

    reroute_inputs["mass_casualty_mode"] = (
        mass_casualty_mode
    )

    compute_triage(reroute_inputs)


result: TriageResult | None = (
    st.session_state["last_result"]
)

meta = st.session_state["last_meta"]
error = st.session_state["last_error"]


# ===========================================================================
# CENTER: RECOMMENDATION + ACTIONS
# ===========================================================================

with center:

    st.markdown(
        '<div class="section-header">Recommendation &amp; Actions</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="card">', unsafe_allow_html=True)

    if error:

        st.error(error)

    elif result is None:

        render_empty_state(
            "🧭",
            "Awaiting assessment",
            (
                "Enter the patient's first-minute data and run "
                "the triage engine to generate an ESI recommendation."
            ),
        )

    else:

        if result.mass_casualty_mode:

            st.markdown(
                """
                <div class="mcm-banner">
                    ⚠ MASS CASUALTY RESULT · DETERMINISTIC VITALS-ONLY ROUTING
                </div>
                """,
                unsafe_allow_html=True,
            )

        elif meta is not None and meta.used_nlp_fallback:

            st.markdown(
                """
                <div class="fallback-banner">
                    NLP MODEL UNAVAILABLE · KEYWORD FALLBACK USED
                </div>
                """,
                unsafe_allow_html=True,
            )

        color = ESI_COLORS[result.esi_level]

        st.markdown(
            f"""
            <div
                class="esi-badge"
                style="background:{color};"
            >
                ESI {result.esi_level}
            </div>

            <div class="esi-label">
                {ESI_LABELS[result.esi_level]}
            </div>

            <div class="esi-sub">
                Risk Score {result.risk_score:.2f}
                · Recommended — nurse confirms
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ---------------------------------------------------------------
        # Quick metrics
        # ---------------------------------------------------------------

        m1, m2 = st.columns(2)

        with m1:
            render_metric(
                "Risk score",
                f"{result.risk_score:.2f}",
            )

        with m2:

            latency = (
                f"{meta.latency_ms:.1f} ms"
                if meta is not None
                else "—"
            )

            render_metric(
                "Latency",
                latency,
            )

        st.markdown(
            '<div class="action-title">Clinical recommendation</div>',
            unsafe_allow_html=True,
        )

        st.info(
            ESI_DESCRIPTIONS[result.esi_level]
        )

        st.markdown(
            '<div class="action-title">Auto-triggered actions</div>',
            unsafe_allow_html=True,
        )

        if result.decisions:

            for decision in result.decisions:

                st.markdown(
                    f"""
                    <div class="decision-item">
                        {decision}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        else:

            st.markdown(
                """
                <div class="no-decision">
                    ✓ No automatic action triggered.
                    Recommendation remains nurse-confirmed.
                </div>
                """,
                unsafe_allow_html=True,
            )

        if result.reason:

            st.markdown(
                f"""
                <div class="reason-box">
                    <strong>Why:</strong> {result.reason}
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ---------------------------------------------------------------
        # NLP metadata
        # ---------------------------------------------------------------

        if (
            meta is not None
            and not result.mass_casualty_mode
            and meta.nlp_label is not None
        ):

            st.markdown(
                '<div class="action-title">NLP signal</div>',
                unsafe_allow_html=True,
            )

            n1, n2 = st.columns(2)

            with n1:
                render_metric(
                    "Category",
                    meta.nlp_label,
                )

            with n2:
                confidence = (
                    f"{meta.nlp_confidence:.2f}"
                    if meta.nlp_confidence is not None
                    else "—"
                )

                render_metric(
                    "Confidence",
                    confidence,
                )

        # ---------------------------------------------------------------
        # Coherence note
        # ---------------------------------------------------------------

        if (
            meta is not None
            and meta.error_recovery_steps
            and any(
                "coherence"
                in step.lower()
                for step in meta.error_recovery_steps
            )
        ):

            st.markdown(
                """
                <div class="coherence-banner">
                    ✓ Recommendation aligned with the triggered
                    high-priority decision.
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)


# ===========================================================================
# RIGHT: EXPLAINABILITY
# ===========================================================================

with right:

    st.markdown(
        '<div class="section-header">Explainability</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="card">', unsafe_allow_html=True)

    if error or result is None:

        render_empty_state(
            "🔍",
            "No explanation yet",
            (
                "After assessment, this panel decomposes "
                "the risk score into vital, NLP, and age contributions."
            ),
        )

    elif result.explain is None:

        render_empty_state(
            "⚡",
            "Deterministic routing",
            (
                "Mass Casualty Mode bypasses the weighted NLP pipeline. "
                "There is no α / β / γ attribution in this mode."
            ),
        )

    else:

        e = result.explain

        st.markdown(
            f"""
            <div class="formula">
                Risk = {e.alpha:.1f} × Vitals
                     + {e.beta:.1f} × NLP
                     + {e.gamma:.1f} × Age
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ---------------------------------------------------------------
        # Vital factor
        # ---------------------------------------------------------------

        st.markdown(
            f"""
            <div class="factor-label">
                <span>Vital Deviation</span>
                <span class="factor-raw">
                    raw {e.vital_deviation:.2f}
                </span>
            </div>

            <div class="weight-line">
                Weight α = {e.alpha:.2f}
                · Contribution = {e.alpha_contribution:.2f}
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.progress(
            min(
                1.0,
                max(
                    0.0,
                    e.alpha_contribution,
                ),
            ),
        )

        # ---------------------------------------------------------------
        # NLP factor
        # ---------------------------------------------------------------

        st.markdown(
            f"""
            <div class="factor-label">
                <span>NLP Urgency</span>
                <span class="factor-raw">
                    raw {e.nlp_urgency:.2f}
                </span>
            </div>

            <div class="weight-line">
                Weight β = {e.beta:.2f}
                · Contribution = {e.beta_contribution:.2f}
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.progress(
            min(
                1.0,
                max(
                    0.0,
                    e.beta_contribution,
                ),
            ),
        )

        # ---------------------------------------------------------------
        # Age factor
        # ---------------------------------------------------------------

        st.markdown(
            f"""
            <div class="factor-label">
                <span>Age Factor</span>
                <span class="factor-raw">
                    raw {e.age_factor:.2f}
                </span>
            </div>

            <div class="weight-line">
                Weight γ = {e.gamma:.2f}
                · Contribution = {e.gamma_contribution:.2f}
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.progress(
            min(
                1.0,
                max(
                    0.0,
                    e.gamma_contribution,
                ),
            ),
        )

        st.markdown(
            """
            <div class="reason-box">
                <strong>Interpretation:</strong>
                The final risk score is the weighted combination of
                physiological deviation, NLP urgency, and age-related risk.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


# ===========================================================================
# FOOTER
# ===========================================================================

st.markdown(
    """
    <div class="footer">
        PatientTriage.ai · MMTG Emergency Department Decision Support Prototype
        · AI-assisted · Human clinical confirmation required
    </div>
    """,
    unsafe_allow_html=True,
)