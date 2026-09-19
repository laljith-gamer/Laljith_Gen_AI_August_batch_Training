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
    st.subheader("Improve your resume for a target role")
    st.markdown(
        "Tailor your application for a specific position. The system identifies skill gaps, "
        "recommends stronger action-oriented bullet points, and proposes a tailored summary "
        "**strictly grounded in your verified experience** without inventing qualifications."
    )

    if not AppStateManager.is_profile_approved():
        with st.container(border=True):
            st.warning("Review your profile before continuing · Resume tailoring requires a confirmed candidate profile.")
            if st.button("Review profile →", type="primary"):
                AppStateManager.set_active_view("Profile")
                st.rerun()
        return

    profile = AppStateManager.get_approved_profile()

    # Load available jobs for target selection
    job_options = {}
    selected_job: Optional[JobPosting] = st.session_state.get("selected_job_for_cv")

    if settings.JOBS_DATA_PATH.exists():
        df = pd.read_csv(settings.JOBS_DATA_PATH)
        for _, row in df.iterrows():
            label = f"{row['title']} — {row['company']} ({row['location']})"
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

    # Target Job Selector
    target_labels = list(job_options.keys())
    default_idx = 0
    if selected_job:
        for idx, lbl in enumerate(target_labels):
            if job_options[lbl].job_id == selected_job.job_id:
                default_idx = idx
                break

    with st.container(border=True):
        sel_col1, sel_col2 = st.columns([3, 1])
        with sel_col1:
            chosen_label = st.selectbox(
                "Target job posting:",
                options=target_labels,
                index=default_idx if target_labels else 0,
                help="Choose the role you want to tailor your resume for.",
            )
        with sel_col2:
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            if st.button("Back to job matches"):
                AppStateManager.set_active_view("Jobs")
                st.rerun()

    if chosen_label and job_options:
        new_job = job_options[chosen_label]
        # Invalidate previous suggestions if target job changed
        if selected_job is None or new_job.job_id != getattr(selected_job, "job_id", None):
            selected_job = new_job
            st.session_state.selected_job_for_cv = new_job
            st.session_state.cv_suggestions = None

    if not selected_job:
        with st.container(border=True):
            st.info("Please select a target role above or choose one from the Jobs tab.")
        return

    # Target Job Context Summary
    with st.expander(f"Job requirements: {selected_job.title} at {selected_job.company}", expanded=False):
        st.markdown(f"**Location:** {selected_job.location}")
        st.markdown(f"**Required skills:** {', '.join(selected_job.skills)}")
        st.markdown(f"**Description:**\n{selected_job.description}")

    # Generate Trigger
    suggestions: Optional[CVSuggestionResult] = st.session_state.get("cv_suggestions")

    if suggestions is None:
        with st.container(border=True):
            st.markdown(f"**Ready to analyze your resume for:** `{selected_job.title}` at `{selected_job.company}`")
            st.caption("The analysis compares your verified experience with the job description to suggest improvements.")
            if st.button("Analyze resume for this role", type="primary"):
                with st.spinner("Analyzing resume against target requirements..."):
                    engine = CVSuggestionEngine(api_key=AppStateManager.get_api_key())
                    suggestions = engine.generate_suggestions(profile, selected_job)
                    st.session_state.cv_suggestions = suggestions
                    AppStateManager.set_workflow_state(WorkflowState.CV_ANALYZED)
                    AuditLogger.log_event("CV_SUGGESTIONS_GENERATED", "AI", "SUCCESS", {
                        "target_job_id": selected_job.job_id,
                        "target_title": selected_job.title,
                    })
                    st.rerun()
        return

    st.markdown("---")

    # 1. Skill Gaps
    st.markdown("#### 1. Skill gaps for this role")
    st.caption("Skills specified in the job posting that are not currently in your confirmed profile.")
    if suggestions.missing_skills:
        st.markdown(" ".join([f"`{sk}`" for sk in suggestions.missing_skills]))
    else:
        st.success("Your confirmed profile covers all primary technical requirements for this role.")

    st.markdown("---")

    # 2. Bullet Point Improvements (Before vs Suggested)
    st.markdown("#### 2. Bullet point improvements")
    st.caption("Original bullet points paired with impact-oriented rewrites emphasizing measurable results.")
    for idx, critique in enumerate(suggestions.weak_bullets):
        with st.container(border=True):
            st.caption(f"**Bullet #{idx + 1}**")
            b_col1, b_col2 = st.columns(2)
            with b_col1:
                st.markdown("**Current:**")
                st.markdown(f"> *{critique.original_bullet}*")
                st.caption(f"Note: {critique.weakness_reason}")
            with b_col2:
                st.markdown("**Suggested rewrite:**")
                st.markdown(f"**{critique.suggested_rewrite}**")

    st.markdown("---")

    # 3. Actionable Application Strategy
    if suggestions.actionable_suggestions:
        st.markdown("#### 3. Application strategy recommendations")
        for sug in suggestions.actionable_suggestions:
            st.markdown(f"• {sug}")
        st.markdown("---")

    # 4. Tailored Summary Review Form
    st.markdown("#### 4. Tailored professional summary")
    st.caption("Review the proposed summary tailored for this specific role before saving.")

    with st.form("cv_approval_form"):
        curr_summary = profile.summary or "Not specified."
        with st.container(border=True):
            st.markdown("**Current confirmed summary:**")
            st.markdown(f"> *{curr_summary}*")

        edited_summary = st.text_area(
            "Proposed tailored summary (editable):",
            value=suggestions.rewritten_summary,
            height=110,
            help="You can adjust this tailored summary before approving.",
        )

        st.caption("Review the suggested changes before applying them. Human approval remains authoritative.")

        # Action Buttons
        btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([2, 2, 1, 2])
        with btn_col1:
            approve_changes = st.form_submit_button("Approve changes", type="primary")
        with btn_col2:
            save_edits = st.form_submit_button("Save my edits")
        with btn_col3:
            reject_proposal = st.form_submit_button("Reject")
        with btn_col4:
            regen_proposal = st.form_submit_button("Generate another version")

    if approve_changes:
        suggestions.status = ReviewStatus.APPROVED
        FeedbackManager.record_cv_feedback(selected_job.job_id, "accepted", "Accepted suggestions")
        AuditLogger.log_event("CV_PROPOSAL_ACCEPTED", "USER", "APPROVED", {"job_id": selected_job.job_id})
        st.success("Resume improvements confirmed and saved to your application plan.")

    if save_edits:
        suggestions.rewritten_summary = edited_summary
        suggestions.status = ReviewStatus.HUMAN_EDITED
        FeedbackManager.record_cv_feedback(selected_job.job_id, "edited", "Human edited summary")
        AuditLogger.log_event("CV_PROPOSAL_EDITED", "USER", "HUMAN_EDITED", {"job_id": selected_job.job_id})
        st.success("Custom edits saved to your session.")

    if reject_proposal:
        suggestions.status = ReviewStatus.REJECTED
        FeedbackManager.record_cv_feedback(selected_job.job_id, "rejected", "Rejected by user")
        AuditLogger.log_event("CV_PROPOSAL_REJECTED", "USER", "REJECTED", {"job_id": selected_job.job_id})
        st.info("Suggestions rejected. You can generate a new version or continue with your original resume.")

    if regen_proposal:
        st.session_state.cv_suggestions = None
        FeedbackManager.record_cv_feedback(selected_job.job_id, "regenerated", "Requested new generation")
        st.rerun()
