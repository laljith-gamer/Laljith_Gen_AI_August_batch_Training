"""
Streamlit session state management and workflow state machine for SmartHire GenAI.
"""

from typing import Optional, List, Dict, Any
import streamlit as st
from src.models.enums import WorkflowState, ReviewStatus
from src.models.schemas import (
    ResumeProfile,
    HumanApprovedProfile,
    JobPosting,
    JobMatchResult,
    CVSuggestionResult,
)

class AppStateManager:
    """Manages reactive session state, enforcing strict workflow ordering."""

    @classmethod
    def initialize_state(cls):
        defaults = {
            "workflow_state": WorkflowState.NO_RESUME,
            "uploaded_file_name": None,
            "extracted_resume_text": "",
            "human_profile_container": None,
            "job_matches": [],
            "selected_job_for_cv": None,
            "cv_suggestions": None,
            "mentor_chat_history": [],
            "custom_api_key": "",
            "active_view": "Overview",
            "editing_profile": False,
        }
        for key, val in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = val

    @classmethod
    def set_workflow_state(cls, new_state: WorkflowState):
        st.session_state.workflow_state = new_state

    @classmethod
    def get_workflow_state(cls) -> WorkflowState:
        return st.session_state.get("workflow_state", WorkflowState.NO_RESUME)

    @classmethod
    def set_active_view(cls, view_name: str):
        st.session_state.active_view = view_name

    @classmethod
    def get_active_view(cls) -> str:
        return st.session_state.get("active_view", "Overview")

    @classmethod
    def is_profile_approved(cls) -> bool:
        container: Optional[HumanApprovedProfile] = st.session_state.get("human_profile_container")
        return container is not None and container.is_approved

    @classmethod
    def get_approved_profile(cls) -> Optional[ResumeProfile]:
        container: Optional[HumanApprovedProfile] = st.session_state.get("human_profile_container")
        if container and container.is_approved:
            return container.approved_profile
        return None

    @classmethod
    def invalidate_downstream(cls, full_reset: bool = False):
        """Invalidate dependent states when resume or profile changes."""
        st.session_state.job_matches = []
        st.session_state.selected_job_for_cv = None
        st.session_state.cv_suggestions = None
        if full_reset:
            st.session_state.human_profile_container = None
            st.session_state.extracted_resume_text = ""
            st.session_state.uploaded_file_name = None
            st.session_state.editing_profile = False
            st.session_state.dynamic_resume_json = None
            cls.set_workflow_state(WorkflowState.NO_RESUME)

    @classmethod
    def get_status_summary(cls) -> Dict[str, Any]:
        """Provide a clean, user-centric summary of current workspace progress."""
        container: Optional[HumanApprovedProfile] = st.session_state.get("human_profile_container")
        matches: List[JobMatchResult] = st.session_state.get("job_matches", [])
        selected_job: Optional[JobPosting] = st.session_state.get("selected_job_for_cv")
        suggestions = st.session_state.get("cv_suggestions")

        if container is None:
            profile_badge = "No resume"
            next_action = "Upload resume"
            next_view = "Profile"
            next_hint = "Upload a PDF or DOCX to build your career profile."
        elif not container.is_approved:
            profile_badge = "Review required"
            next_action = "Review profile"
            next_view = "Profile"
            next_hint = "Verify extracted skills and career direction before matching jobs."
        elif not matches:
            profile_badge = "Confirmed"
            next_action = "Explore matching jobs"
            next_view = "Jobs"
            next_hint = "Discover verified roles matching your confirmed competencies."
        elif not selected_job or suggestions is None:
            profile_badge = "Confirmed"
            next_action = "Improve resume"
            next_view = "Resume"
            next_hint = "Select a target role and optimize your application bullet points."
        else:
            profile_badge = "Confirmed"
            next_action = "Consult career mentor"
            next_view = "Mentor"
            next_hint = "Get interview prep frameworks and guidance grounded in verified notes."

        target_role = None
        if container:
            prof = container.approved_profile or container.original_ai_profile
            target_role = prof.target_role

        return {
            "profile_status": profile_badge,
            "target_role": target_role or "Not specified",
            "resume_name": st.session_state.get("uploaded_file_name"),
            "job_count": len(matches),
            "selected_job": selected_job.title if selected_job else None,
            "has_cv_plan": suggestions is not None,
            "next_action": next_action,
            "next_view": next_view,
            "next_hint": next_hint,
        }

    @classmethod
    def get_api_key(cls) -> Optional[str]:
        custom = st.session_state.get("custom_api_key", "").strip()
        if custom:
            return custom
        from src.config import settings
        return settings.GEMINI_API_KEY
