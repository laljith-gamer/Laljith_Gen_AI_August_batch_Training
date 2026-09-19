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
            "active_tab": 0,
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
    def get_api_key(cls) -> Optional[str]:
        custom = st.session_state.get("custom_api_key", "").strip()
        if custom:
            return custom
        from src.config import settings
        return settings.GEMINI_API_KEY
