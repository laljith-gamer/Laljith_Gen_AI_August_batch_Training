"""
Job Matching UI Component displaying Top-N semantic matches and relevance feedback.
Scannable cards, human match insights, and streamlined resume tailoring actions.
"""

from typing import List, Optional
import streamlit as st

from src.models.schemas import JobMatchResult, JobPosting
from src.models.enums import WorkflowState
from src.search.job_search import JobSearchEngine
from src.human_loop.feedback import FeedbackManager
from src.human_loop.audit import AuditLogger
from app.state import AppStateManager

def render_job_matches():
    st.subheader("Explore matching opportunities")
    st.markdown(
        "Semantic matching compares your confirmed profile against active roles in the job corpus. "
        "Select a role to tailor your resume bullet points and address skill gaps."
    )

    if not AppStateManager.is_profile_approved():
        with st.container(border=True):
            st.warning("Review your profile before continuing · Job matching requires a confirmed candidate profile.")
            if st.button("Review profile →", type="primary"):
                AppStateManager.set_active_view("Profile")
                st.rerun()
        return

    profile = AppStateManager.get_approved_profile()

    # Search & Filter Row
    s_col1, s_col2, s_col3 = st.columns([3, 2, 1])
    with s_col1:
        keyword_filter = st.text_input("Keywords or title", placeholder="e.g. Backend, AI/ML, Cloud", label_visibility="collapsed")
    with s_col2:
        loc_filter = st.text_input("Location", placeholder="e.g. San Francisco or Remote", label_visibility="collapsed")
    with s_col3:
        search_clicked = st.button("Search jobs", type="primary")

    with st.expander("Search options"):
        top_k = st.slider("Maximum results to show", min_value=3, max_value=10, value=5)

    # Search Execution
    needs_search = search_clicked or not st.session_state.get("job_matches")
    if needs_search:
        with st.spinner("Finding roles that match your confirmed profile..."):
            engine = JobSearchEngine()
            matches = engine.search_matching_jobs(
                profile,
                top_k=top_k,
                location_filter=loc_filter.strip() if loc_filter else None,
            )
            # Filter locally by keyword if provided
            if keyword_filter.strip():
                kw = keyword_filter.strip().lower()
                matches = [
                    m for m in matches
                    if kw in m.job.title.lower()
                    or kw in m.job.description.lower()
                    or any(kw in s.lower() for s in m.job.skills)
                ]
            st.session_state.job_matches = matches
            AuditLogger.log_event("JOB_SEARCH_EXECUTED", "SYSTEM", "SUCCESS", {
                "target_role": profile.target_role,
                "top_k": top_k,
                "results_count": len(matches),
            })

    matches: List[JobMatchResult] = st.session_state.get("job_matches", [])
    if not matches:
        with st.container(border=True):
            st.info("No matching roles found with the current filters. Try broadening your location or clearing keywords.")
        return

    st.markdown(f"**Found {len(matches)} relevant positions for `{profile.target_role or 'Software Professional'}`:**")

    # Scannable Job Cards
    for idx, match in enumerate(matches):
        job = match.job
        score_pct = int(match.similarity_score * 100)

        if score_pct >= 75:
            match_badge = f":green-badge[Strong match ({score_pct}%)]"
        elif score_pct >= 50:
            match_badge = f":blue-badge[Good match ({score_pct}%)]"
        else:
            match_badge = f":gray-badge[Potential match ({score_pct}%)]"

        with st.container(border=True):
            top_row_info, top_row_action = st.columns([3, 1])
            with top_row_info:
                st.markdown(f"#### {job.title}")
                st.caption(f"{job.company} · {job.location}")
                st.markdown(f"{match_badge} · *Based on semantic similarity with your confirmed profile.*")
            with top_row_action:
                if st.button("Improve resume →", key=f"target_job_{job.job_id}_{idx}", type="primary"):
                    st.session_state.selected_job_for_cv = job
                    st.session_state.cv_suggestions = None  # Reset stale suggestions
                    AppStateManager.set_workflow_state(WorkflowState.JOB_MATCHED)
                    AppStateManager.set_active_view("Resume")
                    st.rerun()

            st.write(job.description[:260] + "..." if len(job.description) > 260 else job.description)

            # Skill overlap
            sk1, sk2 = st.columns(2)
            with sk1:
                st.caption("**Matched skills:**")
                if match.matched_skills:
                    st.markdown(" ".join([f"`{s}`" for s in match.matched_skills]))
                else:
                    st.caption("Conceptual alignment with candidate background.")
            with sk2:
                st.caption("**Areas for growth:**")
                if match.missing_skills:
                    st.markdown(" ".join([f"`{s}`" for s in match.missing_skills[:5]]))
                else:
                    st.caption("All core requirements met.")

            # Why this matches
            if match.match_explanation:
                st.markdown(f"**Why this matches:** {match.match_explanation}")

            # Feedback actions
            f_col1, f_col2, f_col3 = st.columns([5, 1, 1])
            with f_col2:
                if st.button("Relevant", key=f"rel_{job.job_id}_{idx}"):
                    FeedbackManager.record_job_feedback(
                        job.job_id, job.title, "relevant", profile.target_role or "General"
                    )
                    st.toast(f"Marked as relevant: {job.title}")
            with f_col3:
                if st.button("Not relevant", key=f"irrel_{job.job_id}_{idx}"):
                    FeedbackManager.record_job_feedback(
                        job.job_id, job.title, "irrelevant", profile.target_role or "General"
                    )
                    st.toast(f"Marked as not relevant: {job.title}")
