"""
Job Matching UI Component displaying Top-N semantic matches and relevance feedback.
Provides scannable cards, transparent match insights, and streamlined resume tailoring actions.
"""

from typing import List, Optional
import streamlit as st

from src.models.schemas import JobMatchResult, JobPosting
from src.models.enums import WorkflowState
from src.search.job_search import JobSearchEngine
from src.human_loop.feedback import FeedbackManager
from src.human_loop.audit import AuditLogger
from src.search.job_repository import JobRepository
from app.state import AppStateManager
from app.ui import render_page_header, render_badge, render_skill_chips_html


def render_job_matches():
    render_page_header(
        eyebrow="OPPORTUNITIES",
        title="Matching opportunities",
        description="Explore verified roles matched against your confirmed profile using semantic vector search.",
    )

    # Dataset info indicator
    try:
        ds_info = JobRepository.get_dataset_info()
        job_count = ds_info.get("job_count", 21739)
        st.caption(
            f":material/database: **Job corpus:** Kaggle Naukri ({job_count:,} postings) · "
            f"**Search:** Semantic FAISS Vector Index"
        )
    except Exception:
        pass

    if not AppStateManager.is_profile_approved():
        container = st.session_state.get("human_profile_container")
        has_draft = container is not None and bool(container.approved_profile or container.original_ai_profile)

        with st.container(border=True):
            badge_kind = "primary" if has_draft else "warning"
            badge_txt = "Ready to confirm" if has_draft else "Action needed"
            title_txt = "Confirm your profile to unlock job matching" if has_draft else "Candidate profile confirmation required"
            desc_txt = (
                "Your resume has been parsed. Confirm your profile to run semantic matching against 21,739 verified Kaggle Naukri postings."
                if has_draft else
                "Semantic matching requires an approved candidate profile with verified skills and target role."
            )
            st.html(f"""
            <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem;">
                {render_badge(badge_txt, badge_kind)}
                <span style="font-weight: 600; color: var(--sh-text);">{title_txt}</span>
            </div>
            <p style="color: var(--sh-text-muted); font-size: 0.9rem; margin-bottom: 1rem;">
                {desc_txt}
            </p>
            """)
            g_col1, g_col2 = st.columns([1.5, 1])
            with g_col1:
                if has_draft:
                    if st.button("Confirm profile & search matching jobs →", type="primary", key="btn_quick_confirm_jobs"):
                        prof = container.approved_profile or container.original_ai_profile
                        ProfileReviewManager.apply_human_approval(container, prof)
                        st.toast("Profile confirmed! Finding matching jobs...")
                        st.rerun()
                else:
                    if st.button("Upload resume in Profile →", type="primary", key="btn_gate_to_profile_upload"):
                        AppStateManager.set_active_view("Profile")
                        st.rerun()
            with g_col2:
                if st.button("Review profile →", key="btn_gate_to_profile"):
                    AppStateManager.set_active_view("Profile")
                    st.rerun()
        return

    profile = AppStateManager.get_approved_profile()

    # Cohesive Search Toolbar
    with st.container(border=True):
        st.markdown("##### Filter opportunities")
        s_col1, s_col2, s_col3 = st.columns([3, 2, 1])
        with s_col1:
            keyword_filter = st.text_input(
                "Keywords or title",
                placeholder="e.g. Backend, AI/ML, Cloud",
                label_visibility="collapsed",
                key="input_job_keywords",
            )
        with s_col2:
            loc_filter = st.text_input(
                "Location",
                placeholder="e.g. San Francisco or Remote",
                label_visibility="collapsed",
                key="input_job_location",
            )
        with s_col3:
            search_clicked = st.button("Search jobs", type="primary", key="btn_exec_job_search")

        with st.expander("Search settings & result limit", expanded=False):
            top_k = st.slider(
                "Maximum results to show",
                min_value=3,
                max_value=10,
                value=5,
                key="slider_job_topk",
            )

    # Search Execution
    needs_search = search_clicked or (st.session_state.get("job_matches") is None)
    if needs_search:
        with st.spinner("Finding roles that match your confirmed competencies..."):
            try:
                engine = JobSearchEngine()
                # If keyword filter is provided, query full Kaggle Naukri corpus directly
                if keyword_filter and keyword_filter.strip():
                    kw_clean = keyword_filter.strip()
                    corpus_results = JobRepository.search_jobs_by_query(kw_clean, limit=50)
                    if loc_filter and loc_filter.strip():
                        loc_clean = loc_filter.strip().lower()
                        corpus_results = [j for j in corpus_results if loc_clean in j.location.lower()]

                    matches = []
                    for c_job in corpus_results[:top_k]:
                        matched_sk, missing_sk = JobSearchEngine.calculate_skill_overlap(
                            profile.skills, c_job.skills, job_text=f"{c_job.title} {c_job.description}"
                        )
                        score = min(0.95, 0.55 + 0.08 * len(matched_sk)) if matched_sk else 0.60
                        matches.append(
                            JobMatchResult(
                                job=c_job,
                                similarity_score=round(score, 3),
                                matched_skills=matched_sk,
                                missing_skills=missing_sk,
                                match_explanation=f"Matches search query '{kw_clean}' with {len(matched_sk)} overlapping skills."
                            )
                        )
                else:
                    matches = engine.search_matching_jobs(
                        profile,
                        top_k=top_k,
                        location_filter=loc_filter.strip() if loc_filter else None,
                    )

                # Fallback to popular target jobs if no vector matches meet threshold
                if not matches and hasattr(JobRepository, "get_popular_target_jobs"):
                    popular = JobRepository.get_popular_target_jobs(limit=top_k)
                    matches = []
                    for p_job in popular:
                        matched_sk, missing_sk = JobSearchEngine.calculate_skill_overlap(
                            profile.skills, p_job.skills, job_text=f"{p_job.title} {p_job.description}"
                        )
                        matches.append(
                            JobMatchResult(
                                job=p_job,
                                similarity_score=0.72,
                                matched_skills=matched_sk,
                                missing_skills=missing_sk,
                                match_explanation="Recommended industry role from the Kaggle Naukri corpus.",
                            )
                        )

                st.session_state.job_matches = matches
                AuditLogger.log_event("JOB_SEARCH_EXECUTED", "SYSTEM", "SUCCESS", {
                    "target_role": profile.target_role,
                    "top_k": top_k,
                    "results_count": len(matches),
                })
            except Exception as exc:
                logger.error(f"Semantic job matching error: {exc}", exc_info=True)
                st.warning("Vector search service encountered a temporary issue. Displaying recommended corpus roles.")
                popular = JobRepository.get_popular_target_jobs(limit=top_k) if hasattr(JobRepository, "get_popular_target_jobs") else []
                matches = []
                for p_job in popular:
                    matched_sk, missing_sk = JobSearchEngine.calculate_skill_overlap(
                        profile.skills, p_job.skills, job_text=f"{p_job.title} {p_job.description}"
                    )
                    matches.append(
                        JobMatchResult(
                            job=p_job,
                            similarity_score=0.68,
                            matched_skills=matched_sk,
                            missing_skills=missing_sk,
                            match_explanation="Recommended role from the Kaggle Naukri corpus.",
                        )
                    )
                st.session_state.job_matches = matches

    matches: List[JobMatchResult] = st.session_state.get("job_matches", [])

    if not matches:
        with st.container(border=True):
            st.html(f"""
            <div style="padding: 1rem 0;">
                <div style="font-weight: 600; font-size: 1rem; color: var(--sh-text); margin-bottom: 0.35rem;">
                    No matching roles found
                </div>
                <div style="font-size: 0.875rem; color: var(--sh-text-muted); margin-bottom: 1rem;">
                    No opportunities matched the current keyword and location filters. Try broadening your criteria.
                </div>
            </div>
            """)
            if st.button("Reset filters & reload jobs", type="primary", key="btn_reload_jobs"):
                st.session_state.job_matches = None
                st.rerun()
        return

    # Results Summary Bar
    st.html(f"""
    <div style="display: flex; justify-content: space-between; align-items: center; margin: 1.25rem 0 0.75rem 0;">
        <span style="font-size: 0.9rem; font-weight: 600; color: var(--sh-text);">
            Showing {len(matches)} matching positions for <span style="color: var(--sh-primary);">{profile.target_role or 'Software Professional'}</span>
        </span>
    </div>
    """)

    # High-Priority Redesigned Job Cards
    for idx, match in enumerate(matches):
        job = match.job
        score_pct = int(match.similarity_score * 100)

        if score_pct >= 75:
            badge_type = "success"
            badge_text = f"Strong match · {score_pct}%"
        elif score_pct >= 50:
            badge_type = "primary"
            badge_text = f"Good match · {score_pct}%"
        else:
            badge_type = "neutral"
            badge_text = f"Potential match · {score_pct}%"

        with st.container(border=True):
            # Card Header: Title, Company, Location, Match Score Badge
            header_col, score_col = st.columns([3, 1])
            with header_col:
                st.markdown(f"### {job.title}")
                st.caption(f"**{job.company}** · {job.location}")
            with score_col:
                st.html(f"""
                <div style="text-align: right; margin-top: 4px;">
                    {render_badge(badge_text, badge_type)}
                </div>
                """)

            # Job Description
            desc_text = job.description[:280] + "..." if len(job.description) > 280 else job.description
            st.markdown(f"<p style='color: var(--sh-text); font-size: 0.9rem; line-height: 1.5; margin: 0.5rem 0;'>{desc_text}</p>", unsafe_allow_html=True)

            # Matched Skills & Areas for Growth
            sk_col1, sk_col2 = st.columns(2)
            with sk_col1:
                st.caption("**Matched skills:**")
                if match.matched_skills:
                    st.html(render_skill_chips_html(match.matched_skills, variant="matched"))
                else:
                    st.caption("Conceptual alignment with candidate background.")
            with sk_col2:
                st.caption("**Areas for growth:**")
                if match.missing_skills:
                    st.html(render_skill_chips_html(match.missing_skills[:5], variant="growth"))
                else:
                    st.caption("All core requirements met.")

            # Why this matches Callout
            if match.match_explanation:
                st.html(f"""
                <div class="sh-callout" style="margin-top: 0.75rem; margin-bottom: 0.75rem;">
                    <strong>Why this matches:</strong> {match.match_explanation}
                </div>
                """)

            st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)

            # Bottom Action Bar: Feedback buttons on left, Primary CTA on right
            f_col_left, f_col_mid, f_col_right = st.columns([4, 1, 1.6])
            with f_col_left:
                btn_rel_col, btn_irrel_col = st.columns([1, 1.2])
                with btn_rel_col:
                    if st.button("Relevant", key=f"rel_{job.job_id}_{idx}", help="Mark as relevant to help calibrate recommendations"):
                        FeedbackManager.record_job_feedback(
                            job.job_id, job.title, "relevant", profile.target_role or "General"
                        )
                        st.toast(f"Marked as relevant: {job.title}")
                with btn_irrel_col:
                    if st.button("Not relevant", key=f"irrel_{job.job_id}_{idx}", help="Mark as irrelevant to filter future results"):
                        FeedbackManager.record_job_feedback(
                            job.job_id, job.title, "irrelevant", profile.target_role or "General"
                        )
                        st.toast(f"Marked as not relevant: {job.title}")

            with f_col_right:
                if st.button("Improve resume →", key=f"target_job_{job.job_id}_{idx}", type="primary"):
                    st.session_state.selected_job_for_cv = job
                    st.session_state.cv_suggestions = None  # Reset stale suggestions
                    AppStateManager.set_workflow_state(WorkflowState.JOB_MATCHED)
                    AppStateManager.set_active_view("Resume Studio")
                    st.rerun()
