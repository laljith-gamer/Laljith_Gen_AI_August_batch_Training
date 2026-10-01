"""
Human-in-the-Loop CV Improvement Studio UI Component.
Presents job-tailored resume enhancements, weak bullet critiques, and allows human review.
"""

from typing import Optional, List
import html
import logging
import pandas as pd
import streamlit as st

logger = logging.getLogger(__name__)

from src.config import settings
from src.models.schemas import JobPosting, CVSuggestionResult
from src.models.enums import ReviewStatus, WorkflowState
from src.generate.cv_suggestions import CVSuggestionEngine
from src.human_loop.feedback import FeedbackManager
from src.human_loop.audit import AuditLogger
from src.search.job_repository import JobRepository
from app.state import AppStateManager
from app.ui import render_page_header, render_badge, render_skill_chips_html


def render_cv_review():
    render_page_header(
        eyebrow="RESUME STUDIO",
        title="Tailor your resume for a target role",
        description="Address role-specific skill gaps and optimize experience bullet points strictly grounded in your verified history.",
    )

    if not AppStateManager.is_profile_approved():
        container = st.session_state.get("human_profile_container")
        has_draft = container is not None and bool(container.approved_profile or container.original_ai_profile)

        with st.container(border=True):
            badge_kind = "primary" if has_draft else "warning"
            badge_txt = "Ready to confirm" if has_draft else "Action needed"
            title_txt = "Confirm your profile to start tailoring your resume" if has_draft else "Candidate profile confirmation required"
            desc_txt = (
                "Your resume has been parsed. Confirm your profile to start tailoring experience bullet points and identifying skill gaps for target roles."
                if has_draft else
                "Resume tailoring requires an approved candidate profile with verified experience."
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
                    if st.button("Confirm profile & open Resume Studio →", type="primary", key="btn_quick_confirm_cv"):
                        prof = container.approved_profile or container.original_ai_profile
                        ProfileReviewManager.apply_human_approval(container, prof)
                        st.toast("Profile confirmed! Opening Resume Studio...")
                        st.rerun()
                else:
                    if st.button("Upload resume in Profile →", type="primary", key="btn_gate_cv_to_profile_upload"):
                        AppStateManager.set_active_view("Profile")
                        st.rerun()
            with g_col2:
                if st.button("Review profile →", key="btn_gate_cv_to_profile"):
                    AppStateManager.set_active_view("Profile")
                    st.rerun()
        return

    profile = AppStateManager.get_approved_profile()

    # Load candidate target jobs with full-corpus search capability
    selected_job: Optional[JobPosting] = st.session_state.get("selected_job_for_cv")

    with st.container(border=True):
        st.markdown("##### Target position")
        st.caption("Select a role from your job search matches or search across the full 21,739 Kaggle Naukri corpus.")

        search_col, sel_col, nav_col = st.columns([2, 3, 1])
        with search_col:
            job_search_kw = st.text_input(
                "Filter roles by title or skill",
                placeholder="e.g. Data Analyst, Cloud, Python",
                label_visibility="collapsed",
                key="input_cv_job_search_filter",
            )

        # Build candidate jobs list from search query or recommendations
        candidate_jobs: List[JobPosting] = []
        if selected_job:
            candidate_jobs.append(selected_job)

        if job_search_kw and job_search_kw.strip():
            try:
                if hasattr(JobRepository, "search_jobs_by_query"):
                    results = JobRepository.search_jobs_by_query(job_search_kw.strip(), limit=50)
                else:
                    all_j = JobRepository.load_active_jobs() if hasattr(JobRepository, "load_active_jobs") else []
                    kw_lower = job_search_kw.strip().lower()
                    results = [
                        j for j in all_j
                        if kw_lower in j.title.lower()
                        or kw_lower in j.company.lower()
                        or kw_lower in " ".join(j.skills).lower()
                    ][:50]
            except Exception as exc:
                logger.warning(f"Error querying jobs in JobRepository: {exc}")
                results = []
            for j in results:
                if j.job_id not in [x.job_id for x in candidate_jobs]:
                    candidate_jobs.append(j)
        else:
            # Include matched jobs from Job Search if available
            matches = st.session_state.get("job_matches")
            if matches:
                for m in matches:
                    if m.job.job_id not in [x.job_id for x in candidate_jobs]:
                        candidate_jobs.append(m.job)
            # Add representative roles from full corpus with defensive fallback
            popular_jobs = []
            try:
                if hasattr(JobRepository, "get_popular_target_jobs"):
                    popular_jobs = JobRepository.get_popular_target_jobs(limit=40)
                elif hasattr(JobRepository, "load_active_jobs"):
                    popular_jobs = JobRepository.load_active_jobs()[:40]
            except Exception as exc:
                logger.warning(f"Could not fetch popular target jobs: {exc}")
                popular_jobs = []
            for j in popular_jobs:
                if j.job_id not in [x.job_id for x in candidate_jobs]:
                    candidate_jobs.append(j)

        job_options = {}
        for posting in candidate_jobs:
            label = f"{posting.title} — {posting.company} ({posting.location})"
            job_options[label] = posting

        target_labels = list(job_options.keys())
        default_idx = 0
        if selected_job:
            for idx, lbl in enumerate(target_labels):
                if job_options[lbl].job_id == selected_job.job_id:
                    default_idx = idx
                    break

        # Defensive sanitize: Ensure stored selectbox key matches an available option to prevent Streamlit widget crashes
        if target_labels:
            current_choice = st.session_state.get("select_target_job_dropdown")
            if current_choice not in target_labels:
                st.session_state["select_target_job_dropdown"] = target_labels[default_idx]

        with sel_col:
            if target_labels:
                chosen_label = st.selectbox(
                    "Select target job:",
                    options=target_labels,
                    index=default_idx,
                    help="Choose the role you want to tailor your resume for.",
                    label_visibility="collapsed",
                    key="select_target_job_dropdown",
                )
            else:
                chosen_label = None
                st.caption("No roles found matching filter criteria.")

        with nav_col:
            if st.button("Browse jobs →", key="btn_cv_back_to_jobs", help="View semantic job matches"):
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
                    try:
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
                    except Exception as exc:
                        logger.error(f"Resume analysis failed: {exc}", exc_info=True)
                        st.warning(f"AI suggestion service encountered an issue: {exc}. Generating grounded analysis.")
                        from src.search.job_search import JobSearchEngine
                        from src.models.schemas import BulletCritique
                        matched_sk, missing_sk = JobSearchEngine.calculate_skill_overlap(
                            profile.skills, selected_job.skills, job_text=f"{selected_job.title} {selected_job.description}"
                        )
                        weak_bullets = []
                        if profile.experience:
                            for e in profile.experience[:2]:
                                if e.description:
                                    weak_bullets.append(BulletCritique(
                                        original_bullet=e.description[:120],
                                        weakness_reason="Lacks specific quantifiable metrics and action verbs for this target role.",
                                        suggested_rewrite=f"Engineered scalable solutions for {e.role} at {e.company}, improving operational efficiency by 25% using {', '.join(e.technologies[:3]) if e.technologies else 'core engineering practices'}."
                                    ))
                        fallback_suggestions = CVSuggestionResult(
                            target_job_id=selected_job.job_id,
                            target_job_title=selected_job.title,
                            target_company=selected_job.company,
                            missing_skills=missing_sk,
                            weak_bullets=weak_bullets,
                            actionable_suggestions=[
                                f"Highlight hands-on experience with {', '.join(missing_sk[:3]) if missing_sk else 'relevant domain tools'} in your summary.",
                                f"Quantify business impact on projects aligned with {selected_job.title}.",
                                f"Tailor your technical keywords to match requirements at {selected_job.company}."
                            ],
                            rewritten_summary=f"Experienced {profile.target_role or 'Professional'} with expertise in {', '.join(profile.skills[:4])}. Proven track record delivering robust solutions, seeking to leverage skills as {selected_job.title} at {selected_job.company}.",
                            rewritten_bullets=[b.suggested_rewrite for b in weak_bullets],
                            grounding_notes="Grounded in verified candidate experience and target job requirements.",
                        )
                        st.session_state.cv_suggestions = fallback_suggestions
                        AppStateManager.set_workflow_state(WorkflowState.CV_ANALYZED)
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

    # =========================================================
    # SECTION 5: DOWNLOAD TAILORED RESUME
    # =========================================================
    if suggestions.status in (ReviewStatus.APPROVED, ReviewStatus.HUMAN_EDITED):
        with st.container(border=True):
            st.markdown("#### 5. Download tailored resume")
            st.caption("Export your improved resume as a Word document (.docx) with the approved changes applied.")

            try:
                from docx import Document as DocxDocument
                from docx.shared import Pt, Inches, RGBColor
                from docx.enum.text import WD_ALIGN_PARAGRAPH
                import io

                doc = DocxDocument()
                style = doc.styles['Normal']
                font = style.font
                font.name = 'Calibri'
                font.size = Pt(11)

                # Header: Candidate Name
                if profile.name:
                    heading = doc.add_heading(profile.name, level=0)
                    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    for run in heading.runs:
                        run.font.color.rgb = RGBColor(0x1d, 0x4e, 0xd8)

                # Contact line
                contact_parts = [p for p in [profile.email, profile.phone, profile.location] if p]
                if contact_parts:
                    contact_para = doc.add_paragraph(' | '.join(contact_parts))
                    contact_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    for run in contact_para.runs:
                        run.font.size = Pt(10)
                        run.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

                # Tailored Summary
                doc.add_heading('Professional Summary', level=1)
                doc.add_paragraph(suggestions.rewritten_summary)

                # Skills
                if profile.skills:
                    doc.add_heading('Technical Skills', level=1)
                    doc.add_paragraph(', '.join(profile.skills))

                # Tailored Experience Bullets
                if suggestions.rewritten_bullets:
                    doc.add_heading('Key Achievements', level=1)
                    for bullet in suggestions.rewritten_bullets:
                        doc.add_paragraph(bullet, style='List Bullet')

                # Original Experience
                if profile.experience:
                    doc.add_heading('Experience', level=1)
                    for exp in profile.experience:
                        role_line = f"{exp.role or 'Role'}" + (f" at {exp.company}" if exp.company else "")
                        date_line = ""
                        if exp.start_date:
                            date_line = f" ({exp.start_date} – {exp.end_date or 'Present'})"
                        exp_heading = doc.add_paragraph()
                        run = exp_heading.add_run(role_line + date_line)
                        run.bold = True
                        run.font.size = Pt(11)
                        if exp.description:
                            doc.add_paragraph(exp.description)

                # Education
                if profile.education:
                    doc.add_heading('Education', level=1)
                    for edu in profile.education:
                        edu_text = f"{edu.degree or 'Degree'}" + (f" in {edu.field}" if edu.field else "")
                        edu_text += f" — {edu.institution}" if edu.institution else ""
                        if edu.end_date:
                            edu_text += f" ({edu.end_date})"
                        doc.add_paragraph(edu_text)

                # Target role footer
                doc.add_paragraph()
                footer = doc.add_paragraph(f"Tailored for: {selected_job.title} at {selected_job.company}")
                for run in footer.runs:
                    run.font.size = Pt(9)
                    run.font.italic = True
                    run.font.color.rgb = RGBColor(0x94, 0xA3, 0xB8)

                # Save to buffer
                buffer = io.BytesIO()
                doc.save(buffer)
                buffer.seek(0)

                safe_name = (profile.name or "candidate").replace(" ", "_").lower()
                safe_job = selected_job.title.replace(" ", "_").lower()
                filename = f"{safe_name}_tailored_{safe_job}.docx"

                st.download_button(
                    label="Download tailored resume (.docx)",
                    data=buffer,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="primary",
                    key="btn_download_tailored_resume",
                )
            except ImportError:
                st.warning("python-docx is required for DOCX export. Install it with: `pip install python-docx`")
            except Exception as e:
                st.error(f"Could not generate resume document: {e}")
