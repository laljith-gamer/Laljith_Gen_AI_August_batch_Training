"""
Job Matching UI Component displaying Top-N semantic matches and relevance feedback.
"""

from typing import List
import streamlit as st

from src.models.schemas import JobMatchResult, JobPosting
from src.models.enums import WorkflowState
from src.search.job_search import JobSearchEngine
from src.human_loop.feedback import FeedbackManager
from src.human_loop.audit import AuditLogger
from app.state import AppStateManager

def render_job_matches():
    st.subheader("Semantic Job Search & Matching")
    
    if not AppStateManager.is_profile_approved():
        st.warning(
            "🔒 **Human Approval Required**: You must review and approve your candidate profile "
            "before semantic job matching can be performed."
        )
        return

    profile = AppStateManager.get_approved_profile()
    
    # Controls Header
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        loc_filter = st.text_input("Filter by Location (optional)", placeholder="e.g. San Francisco or Remote")
    with col2:
        top_k = st.slider("Number of Matches (Top-K)", min_value=3, max_value=10, value=5)
    with col3:
        st.write("")
        st.write("")
        rerun_search = st.button("🔄 Run Matching", type="primary", use_container_width=True)

    # Execute search if requested or if not yet populated
    if rerun_search or not st.session_state.get("job_matches"):
        with st.spinner("Searching job corpus with FAISS using your approved candidate profile..."):
            engine = JobSearchEngine()
            matches = engine.search_matching_jobs(
                profile,
                top_k=top_k,
                location_filter=loc_filter,
            )
            st.session_state.job_matches = matches
            AuditLogger.log_event("JOB_SEARCH_EXECUTED", "SYSTEM", "SUCCESS", {
                "target_role": profile.target_role,
                "top_k": top_k,
                "results_count": len(matches),
            })

    matches: List[JobMatchResult] = st.session_state.get("job_matches", [])
    if not matches:
        st.info("No matching jobs found matching the criteria. Try lowering the threshold or clearing filters.")
        return

    st.markdown(f"**Found {len(matches)} matching positions for approved role:** `{profile.target_role}`")

    # Render each job as an interactive card
    for idx, match in enumerate(matches):
        job = match.job
        score_pct = int(match.similarity_score * 100)

        with st.container(border=True):
            header_col, score_col = st.columns([3, 1])
            with header_col:
                st.markdown(f"### {job.title}")
                st.caption(f"🏢 **{job.company}** | 📍 {job.location} | ID: `{job.job_id}`")
            with score_col:
                st.metric("Semantic Similarity", f"{score_pct}%", help="Cosine similarity score calculated via dense vector embeddings.")
                st.progress(match.similarity_score)

            st.write(job.description[:280] + "..." if len(job.description) > 280 else job.description)

            # Skills Pills
            skill_col1, skill_col2 = st.columns(2)
            with skill_col1:
                st.markdown("**Matched Skills in Profile:**")
                if match.matched_skills:
                    pills = " ".join([f"`{s}`" for s in match.matched_skills])
                    st.markdown(pills)
                else:
                    st.caption("No direct keyword match; conceptual alignment.")

            with skill_col2:
                st.markdown("**Missing Skills (Areas for Growth):**")
                if match.missing_skills:
                    pills = " ".join([f"`{s}`" for s in match.missing_skills[:6]])
                    st.markdown(pills)
                else:
                    st.caption("All job skills found in profile!")

            st.info(f"💡 **AI Match Insight**: {match.match_explanation}")

            # Feedback and Target Action row
            act_col1, act_col2, act_col3 = st.columns([2, 1, 1])
            with act_col1:
                if st.button(
                    f"🎯 Select for CV Improvement Studio",
                    key=f"target_job_{job.job_id}_{idx}",
                    type="secondary",
                    use_container_width=True,
                ):
                    st.session_state.selected_job_for_cv = job
                    AppStateManager.set_workflow_state(WorkflowState.JOB_MATCHED)
                    st.session_state.active_tab = 4  # CV Improvement tab
                    st.success(f"Selected '{job.title}' for CV Improvement! Navigating...")
                    st.rerun()

            with act_col2:
                if st.button("👍 Relevant", key=f"rel_{job.job_id}_{idx}", use_container_width=True):
                    FeedbackManager.record_job_feedback(
                        job.job_id, job.title, "relevant", profile.target_role or "General"
                    )
                    st.toast(f"Recorded feedback: Relevant for {job.title}")

            with act_col3:
                if st.button("👎 Irrelevant", key=f"irrel_{job.job_id}_{idx}", use_container_width=True):
                    FeedbackManager.record_job_feedback(
                        job.job_id, job.title, "irrelevant", profile.target_role or "General"
                    )
                    st.toast(f"Recorded feedback: Irrelevant for {job.title}")
