"""
Human-in-the-Loop CV Improvement Studio UI Component.
Presents job-tailored resume enhancements, weak bullet critiques, and allows human review.
"""

from typing import Optional, List
import html
import pandas as pd
import streamlit as st

from src.config import settings
from src.models.schemas import JobPosting, CVSuggestionResult
from src.models.enums import ReviewStatus, WorkflowState
from src.generate.cv_suggestions import CVSuggestionEngine
from src.human_loop.feedback import FeedbackManager
from src.human_loop.audit import AuditLogger
from app.state import AppStateManager
from app.ui import render_page_header, render_badge, render_skill_chips_html


def render_cv_review():
    render_page_header(
        eyebrow="RESUME STUDIO",
        title="Tailor your resume for a target role",
        description="Address role-specific skill gaps and optimize experience bullet points strictly grounded in your verified history.",
    )

    if not AppStateManager.is_profile_approved():
        with st.container(border=True):
            st.html(f"""
            <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem;">
                {render_badge('Action needed', 'warning')}
                <span style="font-weight: 600; color: var(--sh-text);">Candidate profile confirmation required</span>
            </div>
            <p style="color: var(--sh-text-muted); font-size: 0.9rem; margin-bottom: 1rem;">
                Resume tailoring requires an approved candidate profile with verified experience.
            </p>
            """)
            if st.button("Review profile →", type="primary", key="btn_gate_cv_to_profile"):
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

    # Target Job Selector Card
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
            st.markdown("##### Target position")
            chosen_label = st.selectbox(
                "Select target job:",
                options=target_labels,
                index=default_idx if target_labels else 0,
                help="Choose the role you want to tailor your resume for.",
                label_visibility="collapsed",
                key="select_target_job_dropdown",
            )
        with sel_col2:
            st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)
            if st.button("Back to job matches", key="btn_cv_back_to_jobs"):
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
            st.info("Select a target role above or choose one from the Jobs tab to begin tailoring.")
        return

    # Collapsible Target Job Requirements
    with st.expander(f"Job requirements: {selected_job.title} at {selected_job.company}", expanded=False):
        st.markdown(f"**Location:** {selected_job.location}")
        st.markdown("**Required skills:**")
        st.html(render_skill_chips_html(selected_job.skills, variant="matched"))
        st.markdown(f"**Description:**\n{selected_job.description}")

    # Analysis Generation Trigger / Empty State
    suggestions: Optional[CVSuggestionResult] = st.session_state.get("cv_suggestions")

    if suggestions is None:
        with st.container(border=True):
            st.markdown(f"### Ready to tailor your resume")
            st.markdown(
                f"Tailor your application specifically for **{selected_job.title}** at **{selected_job.company}**. "
                "Our engine identifies missing keywords, converts passive bullets into metrics-driven achievements, "
                "and prepares a grounded professional summary."
            )
            if st.button("Analyze resume for this role", type="primary", key="btn_run_cv_analysis"):
                with st.spinner("Analyzing resume against target requirements..."):
                    engine = CVSuggestionEngine(api_key=AppStateManager.get_api_key())
                    suggestions = engine.generate_suggestions(profile, selected_job)
                    st.session_state.cv_suggestions = suggestions
                    AppStateManager.set_workflow_state(WorkflowState.CV_ANALYZED)
                    AuditLogger.log_event("CV_SUGGESTIONS_GENERATED", "AI", "SUCCESS", {
                        "target_job_id": selected_job.job_id,
                        "target_title": selected_job.title,
                    })
                    st.toast("Resume analysis complete.")
                    st.rerun()
        return

    # =========================================================
    # SECTION 1: SKILL GAPS
    # =========================================================
    with st.container(border=True):
        st.markdown("#### 1. Skill gaps for this role")
        st.caption("Required job competencies not found in your confirmed profile.")
        if suggestions.missing_skills:
            st.html(render_skill_chips_html(suggestions.missing_skills, variant="growth"))
        else:
            st.html(f"""
            <div style="display: flex; align-items: center; gap: 0.5rem; color: var(--sh-success); font-size: 0.875rem;">
                {render_badge('Complete match', 'success')}
                <span>Your confirmed profile covers all primary technical requirements.</span>
            </div>
            """)

    # =========================================================
    # SECTION 2: BULLET POINT IMPROVEMENTS (Side-by-side)
    # =========================================================
    with st.container(border=True):
        st.markdown("#### 2. Bullet point improvements")
        st.caption("Transform passive duties into quantified, high-impact statements.")

        for idx, critique in enumerate(suggestions.weak_bullets):
            orig_bullet = html.escape(critique.original_bullet)
            suggested_bullet = html.escape(critique.suggested_rewrite)
            weakness_note = html.escape(critique.weakness_reason)

            b_col1, b_col2 = st.columns(2)
            with b_col1:
                st.html(f"""
                <div class="sh-compare-card">
                    <div class="sh-compare-label sh-label-current">CURRENT BULLET #{idx + 1}</div>
                    <p class="sh-quote-text">"{orig_bullet}"</p>
                    <div class="sh-critique-note">Note: {weakness_note}</div>
                </div>
                """)
            with b_col2:
                st.html(f"""
                <div class="sh-compare-card" style="border-left: 3px solid var(--sh-primary);">
                    <div class="sh-compare-label sh-label-suggested">SUGGESTED REWRITE</div>
                    <p class="sh-quote-text" style="font-weight: 500; color: var(--sh-text);">"{suggested_bullet}"</p>
                </div>
                """)

    # =========================================================
    # SECTION 3: APPLICATION STRATEGY
    # =========================================================
    if suggestions.actionable_suggestions:
        with st.container(border=True):
            st.markdown("#### 3. Application strategy recommendations")
            st.caption("Actionable tactics to increase recruiter resonance for this opening.")
            for sug in suggestions.actionable_suggestions:
                st.markdown(f"• {sug}")

    # =========================================================
    # SECTION 4: TAILORED SUMMARY REVIEW FORM
    # =========================================================
    with st.container(border=True):
        st.markdown("#### 4. Tailored professional summary")
        st.caption("Review the suggested summary tailored for this position. Verify and edit before approving.")

        curr_summary = profile.summary or "No summary provided."
        st.html(f"""
        <div class="sh-callout" style="margin-bottom: 1rem;">
            <strong>Current confirmed summary:</strong><br/>
            {html.escape(curr_summary)}
        </div>
        """)

        with st.form("cv_approval_form"):
            edited_summary = st.text_area(
                "Proposed tailored summary (editable):",
                value=suggestions.rewritten_summary,
                height=110,
                help="You can adjust this tailored summary before approving.",
            )

            st.caption("Human governance: Verify all statements before applying them to your application.")

            # Button hierarchy
            btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([2, 2, 2, 1.2])
            with btn_col1:
                approve_changes = st.form_submit_button("Approve changes", type="primary")
            with btn_col2:
                save_edits = st.form_submit_button("Save my edits")
            with btn_col3:
                regen_proposal = st.form_submit_button("Generate another version")
            with btn_col4:
                reject_proposal = st.form_submit_button("Reject")

        if approve_changes:
            suggestions.status = ReviewStatus.APPROVED
            FeedbackManager.record_cv_feedback(selected_job.job_id, "accepted", "Accepted suggestions")
            AuditLogger.log_event("CV_PROPOSAL_ACCEPTED", "USER", "APPROVED", {"job_id": selected_job.job_id})
            st.toast("Resume improvements confirmed and saved.")
            st.rerun()

        if save_edits:
            suggestions.rewritten_summary = edited_summary
            suggestions.status = ReviewStatus.HUMAN_EDITED
            FeedbackManager.record_cv_feedback(selected_job.job_id, "edited", "Human edited summary")
            AuditLogger.log_event("CV_PROPOSAL_EDITED", "USER", "HUMAN_EDITED", {"job_id": selected_job.job_id})
            st.toast("Custom edits saved to your session.")
            st.rerun()

        if reject_proposal:
            suggestions.status = ReviewStatus.REJECTED
            FeedbackManager.record_cv_feedback(selected_job.job_id, "rejected", "Rejected by user")
            AuditLogger.log_event("CV_PROPOSAL_REJECTED", "USER", "REJECTED", {"job_id": selected_job.job_id})
            st.toast("Suggestions rejected.")
            st.rerun()

        if regen_proposal:
            st.session_state.cv_suggestions = None
            FeedbackManager.record_cv_feedback(selected_job.job_id, "regenerated", "Requested new generation")
            st.toast("Regenerating suggestions...")
            st.rerun()
