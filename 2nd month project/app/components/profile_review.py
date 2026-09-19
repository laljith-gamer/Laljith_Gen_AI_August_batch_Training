"""
Human-in-the-Loop Profile Review UI Component.
Provides professional inspection, structured editing, diff tracking, and explicit human approval.
"""

from typing import Optional, List
import streamlit as st

from src.models.enums import ReviewStatus, WorkflowState
from src.models.schemas import ResumeProfile, HumanApprovedProfile
from src.human_loop.review import ProfileReviewManager
from src.human_loop.audit import AuditLogger
from src.parsing.loader import load_document
from src.parsing.resume_parser import parse_resume
from app.state import AppStateManager

def render_profile_review():
    container: Optional[HumanApprovedProfile] = st.session_state.get("human_profile_container")

    # =========================================================
    # STATE 1: NO RESUME UPLOADED YET
    # =========================================================
    if container is None:
        st.subheader("Add your resume")
        st.markdown(
            "Upload a PDF or DOCX file to build your career profile. "
            "Our system extracts your verified background for your review."
        )

        with st.container(border=True):
            uploaded_file = st.file_uploader(
                "Choose your resume file",
                type=["pdf", "docx"],
                help="Supported formats: PDF, DOCX (maximum size: 10 MB)",
                label_visibility="collapsed",
            )
            st.caption("Supported formats: PDF or DOCX · Maximum file size: 10 MB")

            if uploaded_file is not None:
                st.markdown(f"**Selected file:** `{uploaded_file.name}` ({uploaded_file.size / 1024:.1f} KB)")
                if st.button("Analyze resume", type="primary"):
                    with st.spinner("Analyzing your resume..."):
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
                            st.success("Resume analyzed. Please review your profile below.")
                            st.rerun()
                        except Exception as ex:
                            st.error("We couldn't analyze the resume right now. Please check the file and try again.")
                            AuditLogger.log_event("RESUME_PARSE_FAILED", "AI", "ERROR", {"error": str(ex)})
        return

    orig = container.original_ai_profile
    curr = container.approved_profile
    is_editing = st.session_state.get("editing_profile", False)

    # =========================================================
    # STATE 2: PROFILE CONFIRMED (APPROVED) & NOT ACTIVELY EDITING
    # =========================================================
    if container.is_approved and not is_editing:
        top_col1, top_col2 = st.columns([4, 1])
        with top_col1:
            st.subheader("Your confirmed profile")
            st.markdown(
                ":green-badge[Profile confirmed] · Approved and ready for job matching."
            )
        with top_col2:
            if st.button("Edit profile", help="Update skills, target role, or summary"):
                st.session_state.editing_profile = True
                st.rerun()

        # Confirmed Profile Summary Card
        with st.container(border=True):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Name:** {curr.name or 'Not specified'}")
                st.markdown(f"**Email:** {curr.email or 'Not specified'}")
                st.markdown(f"**Phone:** {curr.phone or 'Not specified'}")
                st.markdown(f"**Location:** {curr.location or 'Not specified'}")
            with c2:
                st.markdown(f"**Target Role:** `{curr.target_role or 'Software Professional'}`")
                yoe_str = f"{curr.years_of_experience:.1f} years" if curr.years_of_experience else "Not specified"
                st.markdown(f"**Experience:** {yoe_str}")
                st.markdown(f"**Source File:** `{st.session_state.get('uploaded_file_name', 'resume')}`")

            st.markdown("---")
            st.markdown("**Professional Summary:**")
            st.markdown(f"> *{curr.summary or 'No summary provided.'}*")

            st.markdown("---")
            st.markdown("**Confirmed Competencies:**")
            if curr.skills:
                pills = " ".join([f"`{s}`" for s in curr.skills])
                st.markdown(pills)
            else:
                st.caption("No specific skills listed.")

        # Next Step CTA
        cta_col1, cta_col2 = st.columns([2, 1])
        with cta_col1:
            if st.button("Explore matching jobs →", type="primary"):
                AppStateManager.set_active_view("Jobs")
                st.rerun()
        with cta_col2:
            if st.button("Replace resume", help="Upload a new resume file"):
                AppStateManager.invalidate_downstream(full_reset=True)
                st.rerun()

        # Collapsed Technical details
        with st.expander("Technical details & audit trace"):
            st.caption("Original AI extraction before human review:")
            st.json(orig.model_dump(mode="json"))
            if container.change_summary:
                st.caption(f"Change summary: {container.change_summary}")
        return

    # =========================================================
    # STATE 3: REVIEW REQUIRED OR ACTIVELY EDITING
    # =========================================================
    st.subheader("Review your profile")
    st.markdown(
        "We extracted the details below from your resume. "
        "Review and update any fields before confirming your profile for job matching."
    )

    if container.is_approved and is_editing:
        st.info("You are currently updating your confirmed profile. Save your changes to confirm.")
    else:
        st.warning("Review required · Check your details and approve to unlock matching roles.")

    with st.form("profile_review_form"):
        # Section 1: Personal Information
        st.markdown("##### Personal information")
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name", value=curr.name or "")
            email = st.text_input("Email Address", value=curr.email or "")
        with col2:
            phone = st.text_input("Phone Number", value=curr.phone or "")
            location = st.text_input("Location", value=curr.location or "")

        st.markdown("---")

        # Section 2: Career Direction
        st.markdown("##### Career direction")
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
        st.markdown("##### Skills & competencies")
        skills_str = st.text_area(
            "Skills (comma-separated)",
            value=", ".join(curr.skills) if curr.skills else "",
            help="Add or adjust technical skills, frameworks, languages, and tools.",
        )

        st.markdown("---")

        # Section 4: Professional Summary
        st.markdown("##### Professional summary")
        summary = st.text_area(
            "Summary Statement",
            value=curr.summary or "",
            height=110,
            help="Your primary career objective or background overview.",
        )

        # Section 5: Experience & Education Preview
        if curr.education or curr.experience:
            st.markdown("---")
            st.markdown("##### Education & background")
            for edu in curr.education:
                st.caption(f"• **{edu.institution or 'Institution'}** — {edu.degree or ''} ({edu.start_date or ''} - {edu.end_date or ''})")

        st.markdown("---")

        # Action Buttons
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
        st.success("Profile confirmed. You can now explore matching opportunities.")
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
        st.success("Changes saved and profile confirmed.")
        st.rerun()

    if restore_ai:
        container.reset_to_ai()
        AppStateManager.set_workflow_state(WorkflowState.PROFILE_REVIEW)
        st.session_state.editing_profile = False
        AuditLogger.log_event("PROFILE_RESET", "USER", "RESET", {})
        st.info("Profile restored to initial extraction.")
        st.rerun()

    # Secondary Action: Replace Resume
    st.markdown("---")
    r_col1, r_col2 = st.columns([4, 1])
    with r_col2:
        if st.button("Replace resume", help="Discard current profile and upload a new resume"):
            AppStateManager.invalidate_downstream(full_reset=True)
            st.rerun()

    # Technical Details
    with st.expander("Technical details"):
        st.caption("Raw extracted JSON:")
        st.json(orig.model_dump(mode="json"))
