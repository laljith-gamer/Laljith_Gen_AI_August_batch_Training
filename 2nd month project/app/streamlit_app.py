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
from app.ui import (
    inject_global_styles,
    render_page_header,
    render_badge,
    render_workflow_stepper,
    render_sidebar_brand,
    render_sidebar_status_widget,
    render_metric_card,
)
from app.components.profile_review import render_profile_review
from app.components.job_cards import render_job_matches
from app.components.cv_review import render_cv_review
from app.components.mentor_chat import render_mentor_chat

st.set_page_config(
    page_title="SmartHire | Career Intelligence Workspace",
    page_icon=":material/work:",
    layout="wide",
    initial_sidebar_state="expanded",
)

AppStateManager.initialize_state()
if "view" in st.query_params:
    q_view = st.query_params.get("view")
    if q_view:
        AppStateManager.set_active_view(q_view)
active_theme = AppStateManager.get_theme_mode()

# Inject centralized styling tokens and layout rules (theme-aware)
inject_global_styles(theme_mode=active_theme)

# --- SIDEBAR APP SHELL ---
with st.sidebar:
    render_sidebar_brand()

    st.html('<div class="sh-nav-section-label">WORKSPACE</div>')

    current_view = AppStateManager.get_active_view()

    workspace_items = [
        ("Overview", ":material/dashboard:  Overview"),
        ("Profile", ":material/account_circle:  Profile"),
        ("Jobs", ":material/work:  Jobs"),
        ("Resume Studio", ":material/description:  Resume Studio"),
        ("Career Mentor", ":material/psychology:  Career Mentor"),
    ]

    for view_key, view_label in workspace_items:
        is_active = current_view == view_key
        btn_type = "primary" if is_active else "secondary"
        if st.button(view_label, key=f"nav_btn_{view_key}", type=btn_type, width="stretch"):
            if current_view != view_key:
                AppStateManager.set_active_view(view_key)
                st.rerun()


    st.html('<div class="sh-nav-section-label">WORKFLOW STATUS</div>')
    summary = AppStateManager.get_status_summary()
    render_sidebar_status_widget(summary)


    st.html('<div class="sh-nav-section-label">TOOLS</div>')
    tools_items = [
        ("Evaluation", ":material/analytics:  Evaluation"),
        ("Settings", ":material/settings:  Settings"),
    ]

    for tool_key, tool_label in tools_items:
        is_active = current_view == tool_key
        btn_type = "primary" if is_active else "secondary"
        if st.button(tool_label, key=f"nav_btn_{tool_key}", type=btn_type, width="stretch"):
            if current_view != tool_key:
                AppStateManager.set_active_view(tool_key)
                st.rerun()

    st.html('<div class="sh-nav-section-label">APPEARANCE</div>')
    theme_options = ["Light", "Dark"]
    theme_display_map = {"Light": "Light", "Dark": "Dark"}

    def _on_sidebar_theme_changed():
        choice = st.session_state.get("sidebar_theme_choice")
        if choice:
            AppStateManager.set_theme_mode(choice.lower())

    st.segmented_control(
        "Theme Mode",
        options=theme_options,
        format_func=lambda x: theme_display_map[x],
        key="sidebar_theme_choice",
        on_change=_on_sidebar_theme_changed,
        label_visibility="collapsed",
    )

    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
    st.caption("SmartHire v1.0 · Grounded Career Intelligence")

# --- MAIN WORKSPACE ROUTING ---
active_view = AppStateManager.get_active_view()

# --- OVERVIEW ---
if active_view == "Overview":
    render_page_header(
        eyebrow="CAREER WORKSPACE",
        title="Your career workspace",
        description="Review your verified profile, discover matching roles, and prepare targeted applications.",
    )

    summary = AppStateManager.get_status_summary()
    state_key = summary.get("state_key", "NO_RESUME")

    # Dynamic Hero Next Action Card
    card_border_cls = "confirmed" if summary["profile_status"] == "Confirmed" else ("review-required" if summary["profile_status"] == "Review required" else "")

    if state_key == "NO_RESUME":
        hero_badge = render_badge("Step 1 of 5", "neutral")
        hero_title = "Add your resume to begin"
        hero_desc = "Upload your resume document to extract verified competencies, evaluate matching roles, and tailor applications."
        hero_cta = "Add your resume →"
    elif state_key == "REVIEW_REQUIRED":
        hero_badge = render_badge("Action needed", "warning")
        hero_title = "Profile review required"
        hero_desc = "The AI extracted competencies from your resume. Verify and confirm your profile to unlock job matching."
        hero_cta = "Review & confirm profile →"
    elif state_key == "PROFILE_CONFIRMED":
        hero_badge = render_badge("Profile confirmed", "success")
        hero_title = "Discover matching opportunities"
        hero_desc = "Your competencies are verified. Explore semantic job matches tailored to your career direction."
        hero_cta = "Explore matching jobs →"
    elif state_key == "JOBS_FOUND":
        hero_badge = render_badge("Roles discovered", "primary")
        hero_title = "Tailor your resume for a target role"
        hero_desc = "Select a position in Resume Studio to identify skill gaps and optimize experience bullet points."
        hero_cta = "Open Resume Studio →"
    else:
        hero_badge = render_badge("Workspace ready", "success")
        hero_title = "Consult your grounded career mentor"
        hero_desc = "Prepare for behavioral interviews and explore role transitions grounded in verified roadmaps."
        hero_cta = "Open Career Mentor →"

    with st.container(border=True):
        st.html(f"""
        <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
            {hero_badge}
        </div>
        """)
        h_col1, h_col2 = st.columns([3, 1])
        with h_col1:
            st.markdown(f"### {hero_title}")
            st.markdown(f"<p style='color: var(--sh-text-muted); font-size: 0.95rem; margin: 0;'>{hero_desc}</p>", unsafe_allow_html=True)
        with h_col2:
            st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
            if st.button(hero_cta, type="primary", key="btn_hero_next_action"):
                AppStateManager.set_active_view(summary["next_view"])
                st.rerun()

    # Workflow Stepper Visualization
    st.markdown("#### Workflow progress")
    has_resume = summary["resume_name"] is not None
    is_approved = summary["profile_status"] == "Confirmed"
    has_jobs = summary["job_count"] > 0
    has_cv = summary["has_cv_plan"]
    has_chat = len(st.session_state.get("mentor_chat_history", [])) > 0

    stages = [
        {
            "num": "01",
            "title": "Resume",
            "state": "completed" if has_resume else "current",
            "caption": summary["resume_name"] or "Pending upload",
        },
        {
            "num": "02",
            "title": "Profile",
            "state": "completed" if is_approved else ("current" if has_resume else "locked"),
            "caption": "Confirmed" if is_approved else ("Review required" if has_resume else "Locked"),
        },
        {
            "num": "03",
            "title": "Jobs",
            "state": "completed" if has_jobs else ("current" if is_approved else "locked"),
            "caption": f"{summary['job_count']} matches" if has_jobs else ("Ready" if is_approved else "Locked"),
        },
        {
            "num": "04",
            "title": "Resume Studio",
            "state": "completed" if has_cv else ("current" if summary["selected_job"] else ("available" if has_jobs else "locked")),
            "caption": (summary["selected_job"][:15] + "...") if summary["selected_job"] else ("Ready" if has_jobs else "Locked"),
        },
        {
            "num": "05",
            "title": "Career Mentor",
            "state": "completed" if has_chat else "available",
            "caption": "Active chat" if has_chat else "Available",
        },
    ]
    render_workflow_stepper(stages)

    # 3 Career Workflow Action Cards
    st.markdown("#### Career workflow")
    c_col1, c_col2, c_col3 = st.columns(3)
    with c_col1:
        with st.container(border=True):
            st.caption("01 · PROFILE")
            st.markdown("##### Review profile")
            st.caption("Ensure your skills, target role, and summary accurately represent your background before AI matching.")
            st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
            if st.button("Open profile", key="btn_open_profile"):
                AppStateManager.set_active_view("Profile")
                st.rerun()

    with c_col2:
        with st.container(border=True):
            st.caption("02 · MATCHING")
            st.markdown("##### Explore roles")
            st.caption("Discover positions matching your verified competencies with clear explanations of why they match.")
            st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
            if st.button("Explore jobs", key="btn_open_jobs"):
                AppStateManager.set_active_view("Jobs")
                st.rerun()

    with c_col3:
        with st.container(border=True):
            st.caption("03 · OPTIMIZATION")
            st.markdown("##### Improve & prepare")
            st.caption("Tailor your experience bullets for a specific position and consult the grounded career mentor.")
            st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
            if st.button("Open Resume Studio", key="btn_open_cv"):
                AppStateManager.set_active_view("Resume Studio")
                st.rerun()

# --- PROFILE REVIEW ---
elif active_view == "Profile":
    render_profile_review()

# --- JOB MATCHES ---
elif active_view == "Jobs":
    render_job_matches()

# --- RESUME STUDIO ---
elif active_view in ("Resume", "Resume Studio"):
    render_cv_review()

# --- CAREER MENTOR ---
elif active_view in ("Mentor", "Career Mentor"):
    render_mentor_chat()

# --- EVALUATION & TELEMETRY ---
elif active_view in ("Evaluation", "Evaluation & Telemetry"):
    render_page_header(
        eyebrow="SYSTEM TELEMETRY",
        title="System benchmarks & evaluation",
        description="Automated benchmarks measuring retrieval hit rate, hallucination refusal accuracy, and human feedback telemetry.",
    )

    ev_col1, ev_col2 = st.columns([1, 3])
    with ev_col1:
        if st.button("Run full evaluation suite", type="primary", key="btn_run_eval"):
            from src.evaluate import SystemEvaluator
            with st.spinner("Running automated benchmarks across subsystems..."):
                evaluator = SystemEvaluator()
                evaluator.run_full_evaluation()
                st.toast("Evaluation suite executed.")
                st.rerun()

    report_json_path = settings.PROJECT_ROOT / "reports/evaluation_results.json"
    if report_json_path.exists():
        with open(report_json_path, "r", encoding="utf-8") as f:
            eval_data = json.load(f)

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            hit_rate = eval_data.get("retrieval_evaluation", {}).get("hit_rate", 0.0)
            render_metric_card("Retrieval Hit Rate", f"{hit_rate * 100:.1f}%", "FAISS knowledge index")
        with m2:
            refusal_rate = eval_data.get("hallucination_evaluation", {}).get("refusal_rate", 0.0)
            render_metric_card("Hallucination Refusal", f"{refusal_rate * 100:.1f}%", "Out-of-scope defense")
        with m3:
            j_rate = eval_data.get("hitl_feedback_metrics", {}).get("job_relevance_rate", 0.0)
            render_metric_card("Job Relevance", f"{j_rate * 100:.1f}%", "User relevance telemetry")
        with m4:
            m_rate = eval_data.get("hitl_feedback_metrics", {}).get("mentor_helpfulness_rate", 0.0)
            render_metric_card("Mentor Helpfulness", f"{m_rate * 100:.1f}%", "Grounded answer rating")

        st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
        with st.expander("Evaluation report summary", expanded=False):
            report_md_path = settings.PROJECT_ROOT / "reports/answer_quality.md"
            if report_md_path.exists():
                st.markdown(report_md_path.read_text(encoding="utf-8"))

    st.markdown("---")
    st.markdown("##### System audit event log")
    recent_logs = AuditLogger.get_recent_logs(limit=20)
    if recent_logs:
        st.dataframe(recent_logs, width="stretch")
    else:
        st.caption("No audit events logged yet.")

# --- SETTINGS ---
elif active_view == "Settings":
    render_page_header(
        eyebrow="CONFIGURATION",
        title="Settings & environment",
        description="Manage API credentials and review active inference and vector search configurations.",
    )

    with st.container(border=True):
        st.markdown("##### API configuration")
        st.caption("Configure or override the Gemini API key for this interactive session.")
        custom_key = st.text_input(
            "Gemini API Key (Session Override)",
            type="password",
            value=st.session_state.get("custom_api_key", ""),
            help="Optional: Leave blank to use configured environment key.",
            key="input_session_api_key",
        )
        if custom_key != st.session_state.get("custom_api_key"):
            st.session_state.custom_api_key = custom_key
            st.toast("API key updated for current session.")

    with st.container(border=True):
        st.markdown("##### Workspace appearance")
        st.caption("Toggle between Light Mode and Dark Mode for the application interface.")

        def _on_settings_theme_changed():
            choice = st.session_state.get("settings_theme_mode_selector")
            if choice:
                AppStateManager.set_theme_mode(choice.lower())

        st.segmented_control(
            "Appearance Mode",
            options=["Light", "Dark"],
            format_func=lambda x: f"{x} Mode",
            key="settings_theme_mode_selector",
            on_change=_on_settings_theme_changed,
            label_visibility="collapsed",
        )
        st.caption(f"Active theme: **{active_theme.capitalize()} Mode**. The theme adapts all surface colors, text hierarchy, container cards, specular buttons, and interactive widgets.")

    with st.container(border=True):
        st.markdown("##### Database & Secrets configuration")
        st.caption("Active configuration loaded via Streamlit Secrets (`st.secrets`) and SQL database persistence:")

        from app.components.mentor_storage import MentorDatabaseManager
        from src.config import get_secret
        db_stat = MentorDatabaseManager.get_status()

        has_secrets = False
        try:
            has_secrets = hasattr(st, "secrets") and len(list(st.secrets.keys())) > 0
        except Exception:
            has_secrets = False

        if st.session_state.get("custom_api_key"):
            key_source = "Session override"
        elif has_secrets and get_secret("GEMINI_API_KEY"):
            key_source = "Streamlit Cloud Secrets (`st.secrets`)"
        elif get_secret("GEMINI_API_KEY"):
            key_source = ".env / Environment variable"
        else:
            key_source = "Not configured"

        st.markdown(f"• **Gemini API Key Source:** `{key_source}`")
        st.markdown(f"• **Database Storage Path:** `{db_stat.get('db_path')}`")
        st.markdown(f"• **Persisted Conversations:** `{db_stat.get('sessions_count', 0)} sessions ({db_stat.get('messages_count', 0)} messages)`")
        st.markdown(f"• **Candidate Memories:** `{db_stat.get('memories_count', 0)} facts`")
        st.markdown(f"• **Streamlit Secrets Active:** `{'Yes' if has_secrets else 'No (using local fallback)'}`")

    with st.container(border=True):
        st.markdown("##### Active engine configuration")
        st.caption("Current model runtime and search parameters:")
        st.markdown(f"• **Primary LLM:** `{settings.GEMINI_MODEL}`")
        st.markdown(f"• **Embedding Model:** `{settings.GEMINI_EMBEDDING_MODEL}` (Dimension: `{settings.EMBEDDING_DIMENSION}`)")
        st.markdown(f"• **Job Search Threshold:** `{settings.SIMILARITY_THRESHOLD}` (Top-K: `{settings.TOP_K_JOBS}`)")
