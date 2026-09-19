"""
Human-in-the-Loop Profile Review UI Component.
Provides side-by-side inspection, full editing capabilities, diff tracking, and explicit approval.
"""

import streamlit as st
from src.models.enums import ReviewStatus, WorkflowState
from src.models.schemas import ResumeProfile, HumanApprovedProfile
from src.human_loop.review import ProfileReviewManager
from src.human_loop.audit import AuditLogger
from app.state import AppStateManager

def render_profile_review():
    container: HumanApprovedProfile = st.session_state.get("human_profile_container")
    if not container:
        st.info("No profile available for review. Please upload a resume first.")
        return

    orig = container.original_ai_profile
    curr = container.approved_profile

    st.subheader("Candidate Profile Review (Human-in-the-Loop)")
    st.markdown(
        "Review the structured candidate profile extracted by Gemini. "
        "You have full control to edit skills, experience, or career goals. "
        "**The system strictly requires your explicit approval before matching jobs.**"
    )

    # Status Banner
    status_colors = {
        ReviewStatus.REQUIRES_REVIEW: "warning",
        ReviewStatus.APPROVED: "success",
        ReviewStatus.HUMAN_EDITED: "info",
        ReviewStatus.REJECTED: "error",
    }
    
    if container.is_approved:
        st.success(
            f"**Status: {container.status.value}** - Approved at {container.reviewed_at or 'recently'}. "
            f"{container.change_summary or ''}"
        )
    else:
        st.warning(
            f"**Status: {container.status.value}** - Review required. Please verify the information below."
        )

    # Form for editing
    with st.form("profile_review_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name", value=curr.name or "")
            email = st.text_input("Email Address", value=curr.email or "")
            phone = st.text_input("Phone Number", value=curr.phone or "")
            location = st.text_input("Location", value=curr.location or "")

        with col2:
            target_role = st.text_input("Target Career Role", value=curr.target_role or "Software Professional")
            yoe = st.number_input(
                "Estimated Years of Experience",
                min_value=0.0,
                max_value=40.0,
                value=float(curr.years_of_experience or 0.0),
                step=0.5,
            )
            skills_str = st.text_area(
                "Technical & Professional Skills (comma-separated)",
                value=", ".join(curr.skills) if curr.skills else "",
                help="Edit or add technical competencies.",
            )

        summary = st.text_area(
            "Professional Summary",
            value=curr.summary or "",
            height=100,
            help="Candidate overview statement.",
        )

        st.markdown("---")
        # Action Buttons inside Form
        btn_col1, btn_col2, btn_col3 = st.columns(3)
        with btn_col1:
            approve_btn = st.form_submit_button("✅ Approve Profile (As Is)", type="primary", use_container_width=True)
        with btn_col2:
            save_edit_btn = st.form_submit_button("✏️ Save Edits & Approve", use_container_width=True)
        with btn_col3:
            reset_btn = st.form_submit_button("🔄 Reset to Original AI", use_container_width=True)

    # Handle Form Actions
    if approve_btn:
        ProfileReviewManager.apply_human_approval(container, curr)
        AppStateManager.set_workflow_state(WorkflowState.PROFILE_APPROVED)
        AuditLogger.log_event("PROFILE_APPROVED", "USER", "APPROVED", {"role": curr.target_role})
        st.success("Profile successfully approved! You can now explore Job Matches.")
        st.rerun()

    if save_edit_btn:
        parsed_skills = [s.strip() for s in skills_str.split(",") if s.strip()]
        edited_profile = curr.model_copy(deep=True)
        edited_profile.name = name.strip() or None
        edited_profile.email = email.strip() or None
        edited_profile.phone = phone.strip() or None
        edited_profile.location = location.strip() or None
        edited_profile.target_role = target_role.strip() or None
        edited_profile.years_of_experience = yoe if yoe > 0 else None
        edited_profile.skills = parsed_skills
        edited_profile.summary = summary.strip() or None

        ProfileReviewManager.apply_human_approval(container, edited_profile)
        AppStateManager.set_workflow_state(WorkflowState.PROFILE_APPROVED)
        AuditLogger.log_event("PROFILE_EDITED_AND_APPROVED", "USER", "HUMAN_EDITED", {
            "change_summary": container.change_summary,
            "target_role": edited_profile.target_role,
        })
        st.success(f"Edits saved & profile approved! ({container.change_summary})")
        st.rerun()

    if reset_btn:
        container.reset_to_ai()
        AppStateManager.set_workflow_state(WorkflowState.PROFILE_REVIEW)
        AuditLogger.log_event("PROFILE_RESET", "USER", "RESET", {})
        st.info("Profile reset to initial AI extraction.")
        st.rerun()

    # Raw AI Extraction Comparison Expander
    with st.expander("🔍 View Raw AI Extracted JSON (Before Human Edits)"):
        st.json(orig.model_dump(mode="json"))
