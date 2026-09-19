"""
Human-in-the-Loop CV Improvement Studio UI Component.
Presents job-tailored resume enhancements, weak bullet critiques, and allows human review.
"""

from typing import Optional, List
import pandas as pd
import streamlit as st

from src.config import settings
from src.models.schemas import JobPosting, CVSuggestionResult
from src.models.enums import ReviewStatus, WorkflowState
from src.generate.cv_suggestions import CVSuggestionEngine
from src.human_loop.feedback import FeedbackManager
from src.human_loop.audit import AuditLogger
from app.state import AppStateManager

def render_cv_review():
    st.subheader("CV Improvement Studio (Human-in-the-Loop)")
    st.markdown(
        "Tailor your resume for a specific target job. Gemini generates concrete, actionable bullet critiques "
        "and summary revisions **strictly grounded in your verified experience** without hallucinating qualifications."
    )

    if not AppStateManager.is_profile_approved():
        st.warning("🔒 **Profile Review Required**: Please approve your candidate profile before generating CV improvements.")
        return

    profile = AppStateManager.get_approved_profile()

    # Load available jobs for target selection
    job_options = {}
    selected_job: Optional[JobPosting] = st.session_state.get("selected_job_for_cv")

    if settings.JOBS_DATA_PATH.exists():
        df = pd.read_csv(settings.JOBS_DATA_PATH)
        for _, row in df.iterrows():
            label = f"{row['title']} - {row['company']} ({row['location']})"
            skills = [s.strip() for s in str(row.get('skills', '')).split(",") if s.strip()]
            posting = JobPosting(
                job_id=str(row['job_id']),
                title=str(row['title']),
                company=str(row['company']),
                location=str(row['location']),
                skills=skills,
                description=str(row['description']),
            )
            job_options[label] = posting

    # Target Job Selector Header
    target_labels = list(job_options.keys())
    default_idx = 0
    if selected_job:
        for idx, lbl in enumerate(target_labels):
            if job_options[lbl].job_id == selected_job.job_id:
                default_idx = idx
                break

    chosen_label = st.selectbox(
        "Select Target Job Posting:",
        options=target_labels,
        index=default_idx if target_labels else 0,
        help="Choose the position you want to optimize your resume for.",
    )

    if chosen_label and job_options:
        new_job = job_options[chosen_label]
        if selected_job is None or new_job.job_id != getattr(selected_job, "job_id", None):
            selected_job = new_job
            st.session_state.selected_job_for_cv = new_job
            st.session_state.cv_suggestions = None

    if not selected_job:
        st.info("Please select a target job posting to proceed.")
        return

    # Target Job Context Card
    with st.expander(f"📌 Target Job Details: **{selected_job.title}** at **{selected_job.company}**", expanded=False):
        st.markdown(f"**Required Skills:** {', '.join(selected_job.skills)}")
        st.markdown(f"**Description:**\n{selected_job.description}")

    # Generation Button
    gen_col1, gen_col2 = st.columns([1, 3])
    with gen_col1:
        generate_clicked = st.button("🚀 Analyze & Generate Suggestions", type="primary", use_container_width=True)

    if generate_clicked or st.session_state.get("cv_suggestions") is None:
        with st.spinner("Analyzing resume against target job requirements with Gemini 3.8 Flash..."):
            engine = CVSuggestionEngine(api_key=AppStateManager.get_api_key())
            suggestions = engine.generate_suggestions(profile, selected_job)
            st.session_state.cv_suggestions = suggestions
            AppStateManager.set_workflow_state(WorkflowState.CV_ANALYZED)
            AuditLogger.log_event("CV_SUGGESTIONS_GENERATED", "AI", "SUCCESS", {
                "target_job_id": selected_job.job_id,
                "target_title": selected_job.title,
            })

    suggestions: CVSuggestionResult = st.session_state.get("cv_suggestions")
    if not suggestions:
        return

    st.markdown("---")

    # 1. Missing Skills & Learning Roadmap
    st.markdown("### 1. Skill Gap Analysis (Areas for Development)")
    st.caption("Skills found in the job posting that are not currently in your verified resume.")
    if suggestions.missing_skills:
        cols = st.columns(min(len(suggestions.missing_skills), 4))
        for i, sk in enumerate(suggestions.missing_skills):
            cols[i % len(cols)].warning(f"🎯 **{sk}**")
    else:
        st.success("🎉 Excellent! Your profile covers all core skills required by this job description.")

    # 2. Weak Bullet Point Critiques
    st.markdown("### 2. Bullet Point Critiques & Impact Rewrites")
    st.caption("Critiques identifying passive voice, lack of metrics, or vague wording, with grounded rewrites.")
    for idx, critique in enumerate(suggestions.weak_bullets):
        with st.container(border=True):
            st.markdown(f"**Original Bullet #{idx+1}:**")
            st.markdown(f"> *\"{critique.original_bullet}\"*")
            st.markdown(f"⚠️ **Why it's weak:** {critique.weakness_reason}")
            st.markdown(f"✨ **Recommended Action-Oriented Rewrite:**")
            st.success(f"**{critique.suggested_rewrite}**")

    # 3. Strategic Actionable Suggestions
    st.markdown("### 3. Actionable Application Strategy")
    for sug in suggestions.actionable_suggestions:
        st.markdown(f"- {sug}")

    # 4. Tailored Summary Review Form
    st.markdown("### 4. Human Review of Tailored Professional Summary")
    with st.form("cv_approval_form"):
        edited_summary = st.text_area(
            "Tailored Summary (Review & Edit):",
            value=suggestions.rewritten_summary,
            height=110,
            help="You can edit this proposed summary before accepting.",
        )
        
        st.markdown("**Polished Experience Bullet Points:**")
        for b in suggestions.rewritten_bullets:
            st.markdown(f"- {b}")

        # Human Review Action Buttons
        btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
        with btn_col1:
            accept_btn = st.form_submit_button("✅ Accept Proposal", type="primary", use_container_width=True)
        with btn_col2:
            edit_save_btn = st.form_submit_button("✏️ Save Custom Edit", use_container_width=True)
        with btn_col3:
            reject_btn = st.form_submit_button("❌ Reject Proposal", use_container_width=True)
        with btn_col4:
            regen_btn = st.form_submit_button("🔄 Regenerate", use_container_width=True)

    if accept_btn:
        suggestions.status = ReviewStatus.APPROVED
        FeedbackManager.record_cv_feedback(selected_job.job_id, "accepted", "Accepted AI suggestions")
        AuditLogger.log_event("CV_PROPOSAL_ACCEPTED", "USER", "APPROVED", {"job_id": selected_job.job_id})
        st.success("CV improvement suggestions accepted and saved!")

    if edit_save_btn:
        suggestions.rewritten_summary = edited_summary
        suggestions.status = ReviewStatus.HUMAN_EDITED
        FeedbackManager.record_cv_feedback(selected_job.job_id, "edited", "Human edited summary")
        AuditLogger.log_event("CV_PROPOSAL_EDITED", "USER", "HUMAN_EDITED", {"job_id": selected_job.job_id})
        st.success("Custom edits saved to your candidate session!")

    if reject_btn:
        suggestions.status = ReviewStatus.REJECTED
        FeedbackManager.record_cv_feedback(selected_job.job_id, "rejected", "Rejected by user")
        AuditLogger.log_event("CV_PROPOSAL_REJECTED", "USER", "REJECTED", {"job_id": selected_job.job_id})
        st.warning("CV suggestions rejected. You can edit manually or re-run analysis.")

    if regen_btn:
        FeedbackManager.record_cv_feedback(selected_job.job_id, "regenerated", "Requested new generation")
        st.session_state.cv_suggestions = None
        st.rerun()
