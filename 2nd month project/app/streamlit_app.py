"""
SmartHire GenAI: Resume Matching + AI Career Mentor
Production Streamlit Application
"""

import sys
from pathlib import Path
import json

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from src.config import settings
from src.models.enums import WorkflowState
from src.parsing.loader import load_document
from src.parsing.resume_parser import parse_resume
from src.human_loop.review import ProfileReviewManager
from src.human_loop.feedback import FeedbackManager
from src.human_loop.audit import AuditLogger
from src.evaluate import SystemEvaluator

from app.state import AppStateManager
from app.components.profile_review import render_profile_review
from app.components.job_cards import render_job_matches
from app.components.cv_review import render_cv_review
from app.components.mentor_chat import render_mentor_chat

# Page Configuration
st.set_page_config(
    page_title="SmartHire GenAI | Resume Matching & Career Mentor",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize Session State
AppStateManager.initialize_state()

# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .stMetric {
        background-color: #F8FAFC;
        padding: 10px;
        border-radius: 8px;
        border: 1px solid #E2E8F0;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# SIDEBAR
# -------------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/artificial-intelligence.png", width=64)
    st.markdown("## **SmartHire GenAI**")
    st.caption("AI-powered resume matching and career guidance with Human-in-the-Loop verification.")
    st.markdown("---")

    # Workflow Progress Indicator
    curr_state = AppStateManager.get_workflow_state()
    st.markdown("### 📋 Workflow Tracker")
    
    stages = [
        ("1. Upload Resume", curr_state != WorkflowState.NO_RESUME),
        ("2. Review Profile (HITL)", AppStateManager.is_profile_approved()),
        ("3. Explore Matching Jobs", len(st.session_state.get("job_matches", [])) > 0),
        ("4. CV Improvement (HITL)", st.session_state.get("cv_suggestions") is not None),
        ("5. AI Career Mentor", len(st.session_state.get("mentor_chat_history", [])) > 0),
    ]

    for label, is_done in stages:
        if is_done:
            st.markdown(f"✅ **{label}**")
        else:
            st.markdown(f"⚪ *{label}*")

    st.markdown("---")
    st.markdown("### ⚙️ Engine Settings")
    st.info(f"**LLM:** `{settings.GEMINI_MODEL}`\n\n**Embedding:** `{settings.GEMINI_EMBEDDING_MODEL}`")

    # Optional Custom API Key input
    custom_key = st.text_input(
        "Gemini API Key (Override)",
        type="password",
        value=st.session_state.get("custom_api_key", ""),
        help="Optional: Leave blank to use configured environment key.",
    )
    if custom_key != st.session_state.get("custom_api_key"):
        st.session_state.custom_api_key = custom_key
        st.success("API Key updated for this session!")

    st.markdown("---")
    st.caption("SmartHire GenAI v1.0 | Google GenAI SDK & FAISS")

# -------------------------------------------------------------
# TOP HEADER
# -------------------------------------------------------------
st.markdown('<div class="main-header">💼 SmartHire GenAI</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Resume Intelligence, Semantic Job Search, Tailored CV Optimization & Grounded AI Career Mentorship</div>',
    unsafe_allow_html=True,
)

# -------------------------------------------------------------
# MAIN TAB NAVIGATION
# -------------------------------------------------------------
tab_names = [
    "🏠 Dashboard",
    "📄 Resume Upload",
    "👤 Profile Review (HITL)",
    "💼 Job Matches",
    "✨ CV Studio (HITL)",
    "🤖 Career Mentor (RAG)",
    "📊 Evaluation & Telemetry",
    "ℹ️ About & Docs",
]

tabs = st.tabs(tab_names)

# -------------------------------------------------------------
# TAB 0: DASHBOARD
# -------------------------------------------------------------
with tabs[0]:
    st.subheader("Welcome to SmartHire GenAI")
    st.markdown(
        "SmartHire GenAI solves the disconnect between candidate resumes and job postings by pairing "
        "dense semantic vector matching with strict **Human-in-the-Loop review** and an **AI Career Mentor** "
        "grounded in verified industry knowledge."
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Indexed Jobs", "20 Roles", help="Verified tech postings in FAISS vector store.")
    with col2:
        st.metric("Knowledge Notes", "7 Guides", help="Curated roadmaps & interview frameworks.")
    with col3:
        st.metric("Approval Status", "Approved" if AppStateManager.is_profile_approved() else "Pending Review")
    with col4:
        st.metric("Primary LLM", "Gemini 3.8 Flash")

    st.markdown("---")
    st.markdown("### 🚀 Quick Start Guide")
    qc1, qc2, qc3 = st.columns(3)
    with qc1:
        with st.container(border=True):
            st.markdown("#### 1. Upload & Parse")
            st.write("Upload your resume in PDF or DOCX format. Gemini extracts your skills and background.")
    with qc2:
        with st.container(border=True):
            st.markdown("#### 2. Review & Approve")
            st.write("Inspect the extracted candidate profile. Make edits to skills or goals and explicitly approve.")
    with qc3:
        with st.container(border=True):
            st.markdown("#### 3. Match & Improve")
            st.write("Discover semantically ranked jobs, generate tailored CV revisions, and chat with your mentor.")

    st.markdown("---")
    st.markdown("### 🧪 Quick Demo Shortcuts")
    st.write("Don't have a resume file handy? Load one of our pre-configured test profiles instantly:")
    
    # Prominent User Resume Loader
    if st.button("🌟 Load Laljith V's Resume (`resume.docx`)", type="primary", use_container_width=True):
        user_resume_path = settings.PROJECT_ROOT / "data/resumes/resume.docx"
        if not user_resume_path.exists():
            user_resume_path = Path(r"C:\Users\ASUS\Desktop\personal\resume.docx")
        if user_resume_path.exists():
            doc_res = load_document(user_resume_path)
            st.session_state.uploaded_file_name = "resume.docx"
            st.session_state.extracted_resume_text = doc_res["text"]
            with st.spinner("Extracting structured candidate profile for Laljith V with Gemini 3.8 Flash..."):
                profile = parse_resume(doc_res["text"], api_key=AppStateManager.get_api_key())
                container = ProfileReviewManager.initialize_review(profile)
                st.session_state.human_profile_container = container
                AppStateManager.set_workflow_state(WorkflowState.PROFILE_REVIEW)
                AuditLogger.log_event("USER_RESUME_LOADED", "USER", "SUCCESS", {"filename": "resume.docx"})
                st.success("Loaded Laljith V's resume! Navigate to the 'Profile Review (HITL)' tab to review.")
                st.rerun()

    d_col1, d_col2 = st.columns(2)
    with d_col1:
        if st.button("📁 Load Demo PDF Resume (Alex Rivera - AI/ML)", use_container_width=True):
            sample_pdf_path = settings.PROJECT_ROOT / "data/resumes/sample_resume.pdf"
            if sample_pdf_path.exists():
                doc_res = load_document(sample_pdf_path)
                st.session_state.uploaded_file_name = "sample_resume.pdf"
                st.session_state.extracted_resume_text = doc_res["text"]
                with st.spinner("Extracting structured candidate profile with Gemini 3.8 Flash..."):
                    profile = parse_resume(doc_res["text"], api_key=AppStateManager.get_api_key())
                    container = ProfileReviewManager.initialize_review(profile)
                    st.session_state.human_profile_container = container
                    AppStateManager.set_workflow_state(WorkflowState.PROFILE_REVIEW)
                    AuditLogger.log_event("DEMO_RESUME_LOADED", "USER", "SUCCESS", {"format": "pdf"})
                    st.success("Loaded demo resume! Switch to 'Profile Review (HITL)' tab to review.")
                    st.rerun()

    with d_col2:
        if st.button("📁 Load Demo DOCX Resume (Alex Rivera - AI/ML)", use_container_width=True):
            sample_docx_path = settings.PROJECT_ROOT / "data/resumes/sample_resume.docx"
            if sample_docx_path.exists():
                doc_res = load_document(sample_docx_path)
                st.session_state.uploaded_file_name = "sample_resume.docx"
                st.session_state.extracted_resume_text = doc_res["text"]
                with st.spinner("Extracting structured candidate profile with Gemini 3.8 Flash..."):
                    profile = parse_resume(doc_res["text"], api_key=AppStateManager.get_api_key())
                    container = ProfileReviewManager.initialize_review(profile)
                    st.session_state.human_profile_container = container
                    AppStateManager.set_workflow_state(WorkflowState.PROFILE_REVIEW)
                    AuditLogger.log_event("DEMO_RESUME_LOADED", "USER", "SUCCESS", {"format": "docx"})
                    st.success("Loaded demo resume! Switch to 'Profile Review (HITL)' tab to review.")
                    st.rerun()

# -------------------------------------------------------------
# TAB 1: RESUME UPLOAD
# -------------------------------------------------------------
with tabs[1]:
    st.subheader("Upload Candidate Resume")
    st.markdown("Upload your existing resume in **PDF** or **DOCX** format. Raw text is normalized and sent to Gemini for structured extraction.")

    uploaded_file = st.file_uploader(
        "Choose a PDF or DOCX file:",
        type=["pdf", "docx"],
        help="Maximum file size 10MB.",
    )

    if uploaded_file is not None:
        if st.button("⚡ Process & Parse Resume", type="primary"):
            with st.spinner(f"Extracting text from {uploaded_file.name}..."):
                file_bytes = uploaded_file.read()
                doc_info = load_document(file_bytes, filename=uploaded_file.name)
                st.session_state.uploaded_file_name = uploaded_file.name
                st.session_state.extracted_resume_text = doc_info["text"]

            with st.spinner("Parsing structured profile with Gemini 3.8 Flash..."):
                try:
                    profile = parse_resume(doc_info["text"], api_key=AppStateManager.get_api_key())
                    container = ProfileReviewManager.initialize_review(profile)
                    st.session_state.human_profile_container = container
                    AppStateManager.set_workflow_state(WorkflowState.PROFILE_REVIEW)
                    AuditLogger.log_event("RESUME_PARSED", "AI", "SUCCESS", {"filename": uploaded_file.name})
                    st.success("Resume parsed successfully! Please proceed to the 'Profile Review (HITL)' tab.")
                except Exception as ex:
                    st.error(f"Resume extraction encountered an issue: {ex}")
                    AuditLogger.log_event("RESUME_PARSE_FAILED", "AI", "ERROR", {"error": str(ex)})

    if st.session_state.get("extracted_resume_text"):
        with st.expander("📄 View Extracted Raw Text Preview"):
            st.text(st.session_state.extracted_resume_text[:2000] + ("..." if len(st.session_state.extracted_resume_text) > 2000 else ""))

# -------------------------------------------------------------
# TAB 2: PROFILE REVIEW (HITL)
# -------------------------------------------------------------
with tabs[2]:
    render_profile_review()

# -------------------------------------------------------------
# TAB 3: JOB MATCHES
# -------------------------------------------------------------
with tabs[3]:
    render_job_matches()

# -------------------------------------------------------------
# TAB 4: CV IMPROVEMENT (HITL)
# -------------------------------------------------------------
with tabs[4]:
    render_cv_review()

# -------------------------------------------------------------
# TAB 5: AI CAREER MENTOR (RAG)
# -------------------------------------------------------------
with tabs[5]:
    render_mentor_chat()

# -------------------------------------------------------------
# TAB 6: EVALUATION & TELEMETRY
# -------------------------------------------------------------
with tabs[6]:
    st.subheader("System Evaluation & Human-in-the-Loop Telemetry")
    st.markdown(
        "Real-time evaluation benchmarks measuring retrieval relevance, hallucination refusal accuracy, "
        "and human feedback telemetry across all subsystems."
    )

    eval_col1, eval_col2 = st.columns([1, 3])
    with eval_col1:
        if st.button("🔄 Run Full Evaluation Suite", type="primary", use_container_width=True):
            with st.spinner("Running automated benchmarks across FAISS, Gemini RAG, and guardrails..."):
                evaluator = SystemEvaluator()
                evaluator.run_full_evaluation()
                st.success("Evaluation benchmarks updated!")
                st.rerun()

    # Load latest evaluation report
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
            st.metric("User Job Relevance", f"{j_rate * 100:.1f}%")
        with m4:
            m_rate = eval_data.get("hitl_feedback_metrics", {}).get("mentor_helpfulness_rate", 0.0)
            st.metric("Mentor Helpfulness", f"{m_rate * 100:.1f}%")

        st.markdown("---")
        st.markdown("### 📋 Evaluation Report Summary")
        report_md_path = settings.PROJECT_ROOT / "reports/answer_quality.md"
        if report_md_path.exists():
            st.markdown(report_md_path.read_text(encoding="utf-8"))

    st.markdown("---")
    st.markdown("### 📜 System Audit Event Log")
    recent_logs = AuditLogger.get_recent_logs(limit=20)
    if recent_logs:
        st.dataframe(recent_logs, use_container_width=True)
    else:
        st.caption("No audit events logged yet.")

# -------------------------------------------------------------
# TAB 7: ABOUT & ARCHITECTURE
# -------------------------------------------------------------
with tabs[7]:
    st.subheader("About SmartHire GenAI")
    st.markdown("""
    **SmartHire GenAI** is an advanced Generative AI career portal engineered with:
    - **Google GenAI SDK (v2.22.0)** with **Gemini 3.8 Flash** & **gemini-embedding-001**
    - **FAISS Vector Search (IndexFlatIP)** for dense cosine similarity matching
    - **First-Class Human-in-the-Loop (HITL)** architecture: raw AI data is never propagated downstream without user review and approval
    - **Grounded Retrieval-Augmented Generation (RAG)** citing verified career roadmaps and job postings
    - **Safety Guardrails** defending against prompt injection, credential exfiltration, and fraudulent requests
    - **Auditability & Telemetry** tracking all critical AI inferences without exposing secrets
    """)

    st.markdown("### Architecture Diagram")
    st.code("""
    Resume Upload (PDF/DOCX)
            │
            ▼
    Document Loader & Normalizer
            │
            ▼
    Gemini 3.8 Flash Structured Parser (Pydantic Schema)
            │
            ▼
       ┌───────────────────────────────┐
       │ HUMAN PROFILE REVIEW (HITL)   │
       │ Actions: Approve / Edit /     │
       │          Reset to AI          │
       └───────────────┬───────────────┘
                       │
                       ▼
             Approved Profile (APPROVED)
                       │
             ┌─────────┴───────────────────────┐
             │                                 │
             ▼                                 ▼
    Profile Embedding                 Target Job Selection
    (gemini-embedding-001)                     │
             │                                 ▼
             ▼                        CV Improvement Engine
    FAISS Job Search                   (Gemini 3.8 Flash)
             │                                 │
             ▼                                 ▼
    Top-N Semantic Job Matches        ┌────────────────────────────────┐
             │                        │ HUMAN CV REVIEW (HITL)         │
             ▼                        │ Actions: Accept / Edit /       │
    Relevance Feedback                │          Reject / Regenerate   │
                                      └────────────────┬───────────────┘
                                                       │
                                                       ▼
                                      AI CAREER MENTOR (RAG)
                                                       │
                                                       ▼
                                           Safety & Scope Guardrails
                                                       │
                                                       ▼
                                            FAISS Knowledge Retriever
                                                       │
                                                       ▼
                                            Grounded Answer + Citations
    """, language="text")
