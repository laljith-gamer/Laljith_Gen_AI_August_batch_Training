"""
Automated headless Streamlit AppTest verifying all views, navigation, and state transitions.
"""

import pytest
from streamlit.testing.v1 import AppTest
from src.models.schemas import ResumeProfile
from src.human_loop.review import ProfileReviewManager
from src.models.enums import WorkflowState


from pathlib import Path

APP_PATH = Path(__file__).resolve().parent.parent / "app" / "streamlit_app.py"

def test_overview_renders():
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    assert len(at.exception) == 0
    # Check that Overview page elements render
    assert at.session_state["active_view"] == "Overview"
    assert len(at.button) > 0


def test_profile_empty_state_renders():
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    at.session_state["active_view"] = "Profile"
    at.run()
    assert len(at.exception) == 0
    # Profile should render empty state when no container is set
    assert at.session_state["human_profile_container"] is None


def test_jobs_locked_when_unapproved():
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    at.session_state["active_view"] = "Jobs"
    at.run()
    assert len(at.exception) == 0
    # Should show review profile button since profile is not approved
    btn_labels = [b.label for b in at.button]
    assert any("Review profile" in lbl for lbl in btn_labels)


def test_resume_studio_locked_when_unapproved():
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    at.session_state["active_view"] = "Resume Studio"
    at.run()
    assert len(at.exception) == 0
    # Should show review profile button since profile is not approved
    btn_labels = [b.label for b in at.button]
    assert any("Review profile" in lbl for lbl in btn_labels)


def test_career_mentor_renders():
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    at.session_state["active_view"] = "Career Mentor"
    at.run()
    assert len(at.exception) == 0
    # Verify ChatGPT controls exist (New chat, Think mode, and Chat Input)
    btn_labels = [b.label for b in at.button]
    assert any("New chat" in lbl for lbl in btn_labels)
    assert any("Think" in lbl for lbl in btn_labels)
    assert len(at.chat_input) > 0




def test_evaluation_view_renders():
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    at.session_state["active_view"] = "Evaluation"
    at.run()
    assert len(at.exception) == 0
    btn_labels = [b.label for b in at.button]
    assert any("evaluation suite" in lbl for lbl in btn_labels)


def test_settings_view_renders():
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    at.session_state["active_view"] = "Settings"
    at.run()
    assert len(at.exception) == 0
    assert len(at.text_input) > 0


def test_approved_profile_unlocks_jobs_and_resume_studio():
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    
    # Simulate an approved profile in session state
    sample_prof = ResumeProfile(
        name="Elena Rostova",
        email="elena@example.com",
        target_role="Machine Learning Engineer",
        skills=["Python", "PyTorch", "NLP", "FastAPI"],
        years_of_experience=4.0,
        summary="Experienced ML engineer building NLP pipelines.",
    )
    container = ProfileReviewManager.initialize_review(sample_prof)
    ProfileReviewManager.apply_human_approval(container, sample_prof)
    
    at.session_state["human_profile_container"] = container
    at.session_state["workflow_state"] = WorkflowState.PROFILE_APPROVED
    
    # 1. Check Profile view shows verified profile
    at.session_state["active_view"] = "Profile"
    at.run()
    assert len(at.exception) == 0
    btn_labels = [b.label for b in at.button]
    assert any("Edit profile" in lbl for lbl in btn_labels)
    assert any("Explore matching jobs" in lbl for lbl in btn_labels)
    
    # 2. Check Jobs view unlocked
    at.session_state["active_view"] = "Jobs"
    at.run()
    assert len(at.exception) == 0
    # Search jobs button should be present
    btn_labels = [b.label for b in at.button]
    assert any("Search jobs" in lbl for lbl in btn_labels)
    
    # 3. Check Resume Studio unlocked
    at.session_state["active_view"] = "Resume Studio"
    at.run()
    assert len(at.exception) == 0
    btn_labels = [b.label for b in at.button]
    assert any("Analyze resume" in lbl or "Back to job matches" in lbl for lbl in btn_labels)


def test_theme_mode_defaults_and_toggle():
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    assert len(at.exception) == 0
    # Default theme should be light
    assert at.session_state.get("theme_mode", "light").lower() == "light"

    # Switch to dark mode
    at.session_state["theme_mode"] = "dark"
    at.run()
    assert len(at.exception) == 0
    assert at.session_state.get("theme_mode") == "dark"

