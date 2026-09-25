"""
Human-in-the-Loop Profile Review UI Component.
Provides professional inspection, structured editing, diff tracking, and explicit human approval.
"""

from typing import Optional, List
import json
import streamlit as st

from src.models.enums import ReviewStatus, WorkflowState
from src.models.schemas import ResumeProfile, HumanApprovedProfile
from src.human_loop.review import ProfileReviewManager
from src.human_loop.audit import AuditLogger
from src.parsing.loader import load_document
from src.parsing.resume_parser import parse_resume
from app.state import AppStateManager
from app.ui import render_page_header, render_badge, render_skill_chips_html


def render_profile_review():
    container: Optional[HumanApprovedProfile] = st.session_state.get("human_profile_container")

    # =========================================================
    # STATE 1: NO RESUME UPLOADED YET
    # =========================================================
    if container is None:
        render_page_header(
            eyebrow="PROFILE SETUP",
            title="Build your verified career profile",
            description="Upload your professional resume document to extract structured competencies, verified skills, and career orientation.",
        )

        with st.container(border=True):
            st.markdown("##### Upload your resume document")
            st.caption("Our extraction engine parses competencies, verified experience, and career direction for your explicit review.")

            uploaded_file = st.file_uploader(
                "Choose your resume file",
                type=["pdf", "docx"],
                help="Supported formats: PDF, DOCX (maximum size: 10 MB)",
                label_visibility="collapsed",
            )

            upload_meta_col1, upload_meta_col2 = st.columns([3, 1])
            with upload_meta_col1:
                st.caption("Accepted file formats: **PDF**, **DOCX** · Maximum file size: **10 MB**")

            if uploaded_file is not None:
                with st.container(border=True):
                    f_col1, f_col2 = st.columns([3, 1])
                    with f_col1:
                        st.markdown(f"**Ready to analyze:** `{uploaded_file.name}`")
                        st.caption(f"Size: {uploaded_file.size / 1024:.1f} KB · Document ready for extraction")
                    with f_col2:
                        st.markdown("<div style='margin-top: 6px;'></div>", unsafe_allow_html=True)
                        if st.button("Analyze resume", type="primary", key="btn_parse_uploaded"):
                            with st.spinner("Analyzing resume structure and competencies..."):
                                try:
                                    file_bytes = uploaded_file.read()
                                    doc_info = load_document(file_bytes, filename=uploaded_file.name)
                                    st.session_state.uploaded_file_name = uploaded_file.name
                                    st.session_state.extracted_resume_text = doc_info["text"]

                                    profile = parse_resume(doc_info["text"], api_key=AppStateManager.get_api_key())
                                    new_container = ProfileReviewManager.initialize_review(profile)
                                    st.session_state.human_profile_container = new_container
                                    AppStateManager.set_workflow_state(WorkflowState.PROFILE_REVIEW)
                                    AppStateManager.invalidate_downstream()
                                    AuditLogger.log_event("RESUME_PARSED", "AI", "SUCCESS", {"filename": uploaded_file.name})
                                    st.toast("Resume parsed successfully.")
                                    st.rerun()
                                except Exception as ex:
                                    st.error("Resume analysis could not be completed. Please ensure the file is a valid PDF or DOCX.")
                                    AuditLogger.log_event("RESUME_PARSE_FAILED", "AI", "ERROR", {"error": str(ex)})
        return

    orig = container.original_ai_profile
    curr = container.approved_profile
    is_editing = st.session_state.get("editing_profile", False)

    # =========================================================
    # STATE 2: PROFILE CONFIRMED (APPROVED) & NOT ACTIVELY EDITING
    # =========================================================
    if container.is_approved and not is_editing:
        render_page_header(
            eyebrow="VERIFIED PROFILE",
            title="Your verified career profile",
            description="Your profile details are confirmed and ready for semantic job matching and resume tailoring.",
        )

        # Status and Edit bar
        st_row1, st_row2 = st.columns([4, 1])
        with st_row1:
            st.html(f"""
            <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem;">
                {render_badge('Profile confirmed', 'success')}
                <span style="font-size: 0.85rem; color: var(--sh-text-muted);">Human verification complete</span>
            </div>
            """)
        with st_row2:
            if st.button("Edit profile", help="Update skills, target role, or summary", key="btn_edit_profile"):
                st.session_state.editing_profile = True
                st.rerun()

        # Confirmed Profile Summary Card
        with st.container(border=True):
            p_col1, p_col2 = st.columns([3, 2])
            with p_col1:
                st.markdown(f"### {curr.name or 'Candidate Profile'}")
                st.markdown(f"**Target Role:** `{curr.target_role or 'Software Professional'}`")
                yoe_str = f"{curr.years_of_experience:.1f} years" if curr.years_of_experience else "Not specified"
                st.caption(f"**Experience:** {yoe_str} · **Location:** {curr.location or 'Not specified'}")
            with p_col2:
                st.caption(f"**Email:** {curr.email or 'Not specified'}")
                st.caption(f"**Phone:** {curr.phone or 'Not specified'}")
                st.caption(f"**Source File:** `{st.session_state.get('uploaded_file_name', 'resume')}`")

            st.markdown("---")
            st.markdown("##### Professional summary")
            st.html(f"""
            <div class="sh-callout">
                {curr.summary or 'No summary provided.'}
            </div>
            """)

            st.markdown("##### Confirmed skills & competencies")
            if curr.skills:
                st.html(render_skill_chips_html(curr.skills, variant="matched"))
            else:
                st.caption("No specific skills listed.")

            if curr.education:
                st.markdown("---")
                st.markdown("##### Education & credentials")
                for edu in curr.education:
                    st.caption(f"• **{edu.institution or 'Institution'}** — {edu.degree or 'Degree'} ({edu.start_date or ''} - {edu.end_date or ''})")

        # Next Step CTA Bar
        cta_col1, cta_col2 = st.columns([3, 1])
        with cta_col1:
            if st.button("Explore matching jobs →", type="primary", key="btn_to_jobs_from_profile"):
                AppStateManager.set_active_view("Jobs")
                st.rerun()
        with cta_col2:
            if st.button("Replace resume", help="Upload a new resume file", key="btn_replace_confirmed"):
                AppStateManager.invalidate_downstream(full_reset=True)
                st.rerun()

        # Collapsed Technical details & JSON Export
        with st.expander("Technical details & JSON export", expanded=False):
            st.caption("Validated candidate JSON profile with required fields:")
            if st.session_state.get("dynamic_resume_json"):
                json_data = json.loads(st.session_state.dynamic_resume_json.to_json_str())
            else:
                json_data = curr.model_dump(mode="json")
            st.json(json_data)

            dl_base = (st.session_state.get("uploaded_file_name") or "profile").replace(".docx", "").replace(".pdf", "")
            st.download_button(
                "📥 Download Profile JSON",
                data=json.dumps(json_data, indent=2),
                file_name=f"{dl_base}.json",
                mime="application/json",
                help="Download this profile as a validated JSON file.",
                key="btn_dl_json_confirmed",
            )
            if container.change_summary:
                st.caption(f"Audit change summary: {container.change_summary}")
        return

    # =========================================================
    # STATE 3: REVIEW REQUIRED OR ACTIVELY EDITING
    # =========================================================
    render_page_header(
        eyebrow="PROFILE REVIEW",
        title="Review your extracted profile",
        description="The AI has extracted the information below from your resume. Verify or edit it before confirming.",
    )

    if container.is_approved and is_editing:
        st.info("You are currently updating your confirmed profile. Save your changes to apply updates.")
    else:
        st.html(f"""
        <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem; padding: 0.75rem 1rem; background: var(--sh-warning-subtle); border: 1px solid var(--sh-warning-border); border-radius: 8px;">
            {render_badge('Review required', 'warning')}
            <span style="font-size: 0.875rem; color: var(--sh-warning);">
                Verify extracted competencies before approving this profile for semantic job matching.
            </span>
        </div>
        """)

    with st.form("profile_review_form"):
        # Section 1: Personal Information
        st.markdown("##### 1. Personal information")
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name", value=curr.name or "")
            email = st.text_input("Email Address", value=curr.email or "")
        with col2:
            phone = st.text_input("Phone Number", value=curr.phone or "")
            location = st.text_input("Location", value=curr.location or "")

        st.markdown("---")

        # Section 2: Career Direction
        st.markdown("##### 2. Career direction")
        cd1, cd2 = st.columns(2)
        with cd1:
            target_role = st.text_input(
                "Target Career Role",
                value=curr.target_role or "Software Engineer",
                help="The primary position or orientation you are seeking.",
            )
        with cd2:
            yoe = st.number_input(
                "Years of Experience",
                min_value=0.0,
                max_value=40.0,
                value=float(curr.years_of_experience or 0.0),
                step=0.5,
                help="Estimated total years of professional or technical experience.",
            )

        st.markdown("---")

        # Section 3: Skills
        st.markdown("##### 3. Skills & competencies")
        skills_str = st.text_area(
            "Skills (comma-separated)",
            value=", ".join(curr.skills) if curr.skills else "",
            help="Add or adjust technical skills, frameworks, languages, and tools.",
        )
        if curr.skills:
            st.caption("Current extracted skills preview:")
            st.html(render_skill_chips_html(curr.skills, variant="matched"))

        st.markdown("---")

        # Section 4: Professional Summary
        st.markdown("##### 4. Professional summary")
        summary = st.text_area(
            "Summary Statement",
            value=curr.summary or "",
            height=110,
            help="Your primary career objective or background overview.",
        )

        # Section 5: Experience & Education Preview
        if curr.education:
            st.markdown("---")
            st.markdown("##### 5. Education & background")
            for edu in curr.education:
                st.caption(f"• **{edu.institution or 'Institution'}** — {edu.degree or 'Degree'} ({edu.start_date or ''} - {edu.end_date or ''})")

        st.markdown("---")

        # Action Buttons Hierarchy
        btn_col1, btn_col2, btn_col3 = st.columns([2, 2, 1])
        with btn_col1:
            approve_as_is = st.form_submit_button("Approve profile", type="primary")
        with btn_col2:
            save_edits = st.form_submit_button("Save changes & approve")
        with btn_col3:
            restore_ai = st.form_submit_button("Restore AI extraction")

    # Handle Form Submissions
    if approve_as_is:
        ProfileReviewManager.apply_human_approval(container, curr)
        AppStateManager.set_workflow_state(WorkflowState.PROFILE_APPROVED)
        st.session_state.editing_profile = False
        AuditLogger.log_event("PROFILE_APPROVED", "USER", "APPROVED", {"role": curr.target_role})
        st.toast("Profile confirmed successfully.")
        st.rerun()

    if save_edits:
        parsed_skills = [s.strip() for s in skills_str.split(",") if s.strip()]
        edited = curr.model_copy(deep=True)
        edited.name = name.strip() or None
        edited.email = email.strip() or None
        edited.phone = phone.strip() or None
        edited.location = location.strip() or None
        edited.target_role = target_role.strip() or None
        edited.years_of_experience = yoe if yoe > 0 else None
        edited.skills = parsed_skills
        edited.summary = summary.strip() or None

        ProfileReviewManager.apply_human_approval(container, edited)
        AppStateManager.set_workflow_state(WorkflowState.PROFILE_APPROVED)
        st.session_state.editing_profile = False
        AuditLogger.log_event("PROFILE_EDITED_AND_APPROVED", "USER", "HUMAN_EDITED", {
            "change_summary": container.change_summary,
            "target_role": edited.target_role,
        })
        st.toast("Changes saved and profile confirmed.")
        st.rerun()

    if restore_ai:
        container.reset_to_ai()
        AppStateManager.set_workflow_state(WorkflowState.PROFILE_REVIEW)
        st.session_state.editing_profile = False
        AuditLogger.log_event("PROFILE_RESET", "USER", "RESET", {})
        st.toast("Profile restored to initial extraction.")
        st.rerun()

    # Secondary Action: Replace Resume
    st.markdown("---")
    r_col1, r_col2 = st.columns([4, 1])
    with r_col2:
        if st.button("Replace resume", help="Discard current profile and upload a new resume", key="btn_replace_editing"):
            AppStateManager.invalidate_downstream(full_reset=True)
            st.rerun()

    # Structured JSON & Export (Secondary Expander)
    with st.expander("Technical details & JSON export", expanded=False):
        st.caption("Validated candidate JSON profile with required fields:")
        if st.session_state.get("dynamic_resume_json"):
            json_data = json.loads(st.session_state.dynamic_resume_json.to_json_str())
        else:
            json_data = orig.model_dump(mode="json")
        st.json(json_data)

        dl_base = (st.session_state.get("uploaded_file_name") or "profile").replace(".docx", "").replace(".pdf", "")
        st.download_button(
            "📥 Download Profile JSON",
            data=json.dumps(json_data, indent=2),
            file_name=f"{dl_base}.json",
            mime="application/json",
            help="Download this profile as a validated JSON file.",
            key="btn_dl_json_review",
        )
