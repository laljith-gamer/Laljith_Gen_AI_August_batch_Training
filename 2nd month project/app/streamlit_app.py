import sys
import site
from pathlib import Path
import json

# Ensure user site-packages (where google-genai, pypdf, faiss are installed) is included in sys.path
user_site = site.getusersitepackages()
if user_site and user_site not in sys.path:
    sys.path.insert(0, user_site)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from src.config import settings
from src.models.enums import WorkflowState
from src.human_loop.audit import AuditLogger
from src.human_loop.feedback import FeedbackManager

from app.state import AppStateManager
from app.components.profile_review import render_profile_review
from app.components.job_cards import render_job_matches
from app.components.cv_review import render_cv_review
from app.components.mentor_chat import render_mentor_chat

st.set_page_config(
    page_title="SmartHire | Career Intelligence Workspace",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

AppStateManager.initialize_state()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### SmartHire")
    st.caption("Career intelligence workspace")

    main_nav_options = ["Overview", "Profile", "Jobs", "Resume", "Mentor"]

    current_view = AppStateManager.get_active_view()
    default_idx = main_nav_options.index(current_view) if current_view in main_nav_options else 0

    selected_nav = st.radio(
        "Career Workflow",
        options=main_nav_options,
        index=default_idx,
        label_visibility="collapsed",
    )

    if selected_nav != current_view and selected_nav in main_nav_options:
        AppStateManager.set_active_view(selected_nav)
        st.rerun()

    st.markdown("---")
    st.caption("WORKSPACE PROGRESS")
    summary = AppStateManager.get_status_summary()

    if summary["profile_status"] == "Confirmed":
        st.markdown(":green-badge[Profile confirmed]")
    elif summary["profile_status"] == "Review required":
        st.markdown(":orange-badge[Review required]")
    else:
        st.markdown(":gray-badge[No resume added]")

    if summary["target_role"] != "Not specified":
        st.caption(f"Target: {summary['target_role']}")
    if summary["job_count"] > 0:
        st.caption(f"Matches: {summary['job_count']} roles")

    st.markdown("---")
    st.caption("UTILITIES")
    util_views = ["Evaluation & Telemetry", "Settings"]

    util_idx = 0
    if current_view in util_views:
        util_idx = util_views.index(current_view) + 1

    selected_util = st.selectbox(
        "Utility Views",
        options=["Workflow view"] + util_views,
        index=util_idx,
        label_visibility="collapsed",
    )

    if selected_util != "Workflow view" and selected_util != current_view:
        AppStateManager.set_active_view(selected_util)
        st.rerun()
    elif selected_util == "Workflow view" and current_view in util_views:
        AppStateManager.set_active_view("Overview")
        st.rerun()

    st.markdown("---")
    st.caption("SmartHire v1.0 · Grounded Career Intelligence")

# --- MAIN CONTENT ---
active_view = AppStateManager.get_active_view()

# --- OVERVIEW ---
if active_view == "Overview":
    st.subheader("Your career workspace")
    st.markdown("Review your profile, explore matching roles, and improve your application.")

    summary = AppStateManager.get_status_summary()

    with st.container(border=True):
        st_col1, st_col2 = st.columns([3, 1])
        with st_col1:
            if summary["profile_status"] == "Confirmed":
                st.markdown(f"### Next step: {summary['next_action']}")
                st.markdown(f"{summary['next_hint']}")
            elif summary["profile_status"] == "Review required":
                st.markdown("### Profile review required")
                st.markdown("Your resume has been analyzed. Verify the extracted competencies before they are used for matching.")
            else:
                st.markdown("### Get started by adding your resume")
                st.markdown("Upload your existing resume to build your verified career profile.")
        with st_col2:
            st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
            if st.button(f"{summary['next_action']} →", type="primary"):
                AppStateManager.set_active_view(summary["next_view"])
                st.rerun()

    st.markdown("#### Progress")
    p1, p2, p3, p4, p5 = st.columns(5)

    has_resume = summary["resume_name"] is not None
    is_approved = summary["profile_status"] == "Confirmed"
    has_jobs = summary["job_count"] > 0
    has_cv = summary["has_cv_plan"]
    has_chat = len(st.session_state.get("mentor_chat_history", [])) > 0

    with p1:
        with st.container(border=True):
            st.caption("1. RESUME")
            st.markdown(f"**{summary['resume_name'] or 'Not uploaded'}**")
            st.caption("✓ Added" if has_resume else "Pending upload")
    with p2:
        with st.container(border=True):
            st.caption("2. PROFILE")
            st.markdown(f"**{summary['profile_status']}**")
            st.caption("✓ Confirmed" if is_approved else ("Action needed" if has_resume else "Pending"))
    with p3:
        with st.container(border=True):
            st.caption("3. JOBS")
            st.markdown(f"**{summary['job_count']} matches**" if has_jobs else "**No search yet**")
            st.caption("✓ Explored" if has_jobs else ("Ready" if is_approved else "Locked"))
    with p4:
        with st.container(border=True):
            st.caption("4. RESUME STUDIO")
            st.markdown(f"**{summary['selected_job'][:18] + '...' if summary['selected_job'] and len(summary['selected_job']) > 18 else (summary['selected_job'] or 'No role selected')}**")
            st.caption("✓ Tailored" if has_cv else ("Role selected" if summary['selected_job'] else "Ready"))
    with p5:
        with st.container(border=True):
            st.caption("5. MENTOR")
            st.markdown("**Grounded RAG**")
            st.caption("✓ Active chat" if has_chat else "Available")

    st.markdown("#### Career workflow")
    c_col1, c_col2, c_col3 = st.columns(3)
    with c_col1:
        with st.container(border=True):
            st.markdown("##### 1. Review profile")
            st.caption("Ensure your skills, target role, and summary accurately represent your background before any AI matching.")
            if st.button("Open profile", key="btn_open_profile"):
                AppStateManager.set_active_view("Profile")
                st.rerun()
    with c_col2:
        with st.container(border=True):
            st.markdown("##### 2. Explore roles")
            st.caption("Discover positions matching your verified competencies with clear explanations of why they match.")
            if st.button("Explore jobs", key="btn_open_jobs"):
                AppStateManager.set_active_view("Jobs")
                st.rerun()
    with c_col3:
        with st.container(border=True):
            st.markdown("##### 3. Improve & prepare")
            st.caption("Tailor your experience bullets for a specific position and consult the grounded career mentor.")
            if st.button("Open mentor", key="btn_open_mentor"):
                AppStateManager.set_active_view("Mentor")
                st.rerun()

# --- PROFILE REVIEW ---
elif active_view == "Profile":
    render_profile_review()

# --- JOB MATCHES ---
elif active_view == "Jobs":
    render_job_matches()

# --- RESUME STUDIO ---
elif active_view == "Resume":
    render_cv_review()

# --- CAREER MENTOR ---
elif active_view == "Mentor":
    render_mentor_chat()

# --- EVALUATION & TELEMETRY ---
elif active_view == "Evaluation & Telemetry":
    st.subheader("Evaluation & system benchmarks")
    st.markdown(
        "Automated benchmarks measuring retrieval hit rate, hallucination refusal accuracy, "
        "and human feedback telemetry across all subsystems."
    )

    ev_col1, ev_col2 = st.columns([1, 3])
    with ev_col1:
        if st.button("Run full evaluation suite", type="primary"):
            from src.evaluate import SystemEvaluator
            with st.spinner("Running automated benchmarks..."):
                evaluator = SystemEvaluator()
                evaluator.run_full_evaluation()
                st.success("Benchmarks updated.")
                st.rerun()

    report_json_path = settings.PROJECT_ROOT / "reports/evaluation_results.json"
    if report_json_path.exists():
        with open(report_json_path, "r", encoding="utf-8") as f:
            eval_data = json.load(f)

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            hit_rate = eval_data.get("retrieval_evaluation", {}).get("hit_rate", 0.0)
            st.metric("Retrieval Hit Rate", f"{hit_rate * 100:.1f}%")
        with m2:
            refusal_rate = eval_data.get("hallucination_evaluation", {}).get("refusal_rate", 0.0)
            st.metric("Hallucination Refusal", f"{refusal_rate * 100:.1f}%")
        with m3:
            j_rate = eval_data.get("hitl_feedback_metrics", {}).get("job_relevance_rate", 0.0)
            st.metric("Job Relevance Feedback", f"{j_rate * 100:.1f}%")
        with m4:
            m_rate = eval_data.get("hitl_feedback_metrics", {}).get("mentor_helpfulness_rate", 0.0)
            st.metric("Mentor Helpfulness", f"{m_rate * 100:.1f}%")

        st.markdown("---")
        st.markdown("#### Evaluation report summary")
        report_md_path = settings.PROJECT_ROOT / "reports/answer_quality.md"
        if report_md_path.exists():
            st.markdown(report_md_path.read_text(encoding="utf-8"))

    st.markdown("---")
    st.markdown("#### System audit event log")
    recent_logs = AuditLogger.get_recent_logs(limit=20)
    if recent_logs:
        st.dataframe(recent_logs)
    else:
        st.caption("No audit events logged yet.")

# --- SETTINGS ---
elif active_view == "Settings":
    st.subheader("Settings & configuration")

    with st.container(border=True):
        st.markdown("#### API configuration")
        custom_key = st.text_input(
            "Gemini API Key (Session Override)",
            type="password",
            value=st.session_state.get("custom_api_key", ""),
            help="Optional: Leave blank to use configured environment key.",
        )
        if custom_key != st.session_state.get("custom_api_key"):
            st.session_state.custom_api_key = custom_key
            st.success("API key updated for current session.")

    with st.container(border=True):
        st.markdown("#### Active engine configuration")
        st.markdown(f"• **Primary LLM:** `{settings.GEMINI_MODEL}`")
        st.markdown(f"• **Embedding Model:** `{settings.GEMINI_EMBEDDING_MODEL}` (Dimension: `{settings.EMBEDDING_DIMENSION}`)")
        st.markdown(f"• **Job Search Threshold:** `{settings.SIMILARITY_THRESHOLD}` (Top-K: `{settings.TOP_K_JOBS}`)")
