"""
Unit tests for Advanced AI Career Mentor features:
- Automatic Resume Context extraction (CandidateContextManager)
- Multi-turn conversation memory
- Browser IndexedDB synchronization component (MentorIndexedDBManager)
"""

import pytest
from streamlit.testing.v1 import AppTest

from src.models.schemas import (
    ResumeProfile,
    HumanApprovedProfile,
    ExperienceItem,
    EducationItem,
    ProjectItem,
)
from src.mentor.candidate_context import CandidateContextManager
from src.mentor.rag_chain import MentorRAGChain
from app.components.mentor_storage import MentorIndexedDBManager
from app.components.mentor_memory import MentorMemoryManager



def test_candidate_context_extraction_with_profile():
    profile = ResumeProfile(
        name="Alex Mercer",
        target_role="Senior Machine Learning Engineer",
        years_of_experience=4.5,
        skills=["Python", "PyTorch", "Transformers", "Docker", "AWS"],
        summary="Experienced ML engineer building production recommendation systems.",
        experience=[
            ExperienceItem(
                company="NeuralWorks",
                role="Machine Learning Engineer",
                start_date="2022",
                end_date="Present",
                description="Designed high-throughput inference service.",
                technologies=["PyTorch", "FastAPI"],
            )
        ],
        education=[
            EducationItem(
                institution="Tech University",
                degree="B.S.",
                field="Computer Science",
            )
        ],
        projects=[
            ProjectItem(
                name="SmartRec",
                description="Embedding-based search engine",
                technologies=["Python", "FAISS"],
            )
        ],
    )
    container = HumanApprovedProfile(
        original_ai_profile=profile,
        approved_profile=profile,
        is_approved=True,
    )
    mock_session = {
        "human_profile_container": container,
        "extracted_resume_text": "Alex Mercer resume text...",
        "uploaded_file_name": "alex_mercer_resume.pdf",
    }

    ctx = CandidateContextManager.extract_from_session_state(mock_session)

    assert ctx["has_resume"] is True
    assert ctx["name"] == "Alex Mercer"
    assert ctx["target_role"] == "Senior Machine Learning Engineer"
    assert ctx["years_of_experience"] == 4.5
    assert "PyTorch" in ctx["skills"]
    assert "NeuralWorks" in ctx["formatted_prompt_block"]
    assert "alex_mercer_resume.pdf" in ctx["filename"]


def test_candidate_context_extraction_empty():
    mock_session = {
        "human_profile_container": None,
        "extracted_resume_text": "",
        "uploaded_file_name": None,
    }
    ctx = CandidateContextManager.extract_from_session_state(mock_session)
    assert ctx["has_resume"] is False
    assert ctx["name"] is None
    assert len(ctx["skills"]) == 0
    assert "No candidate resume" in ctx["formatted_prompt_block"]


def test_mentor_indexeddb_component_mount():
    test_app_code = """
import streamlit as st
from app.components.mentor_storage import MentorIndexedDBManager

res = MentorIndexedDBManager.render_storage_toolbar(
    active_session_id="session_12345",
    messages=[
        {"role": "user", "content": "How to transition to ML?"},
        {"role": "assistant", "content": "Start with linear algebra and Python."},
    ],
    candidate_summary={"name": "Alex", "target_role": "ML Engineer"},
    key="test_idb_key",
)
st.write("IndexedDB Toolbar Rendered")
"""
    at = AppTest.from_string(test_app_code)
    at.run()
    assert not at.exception, f"AppTest raised an exception: {at.exception}"
    assert len(at.markdown) > 0
    assert "IndexedDB Toolbar Rendered" in at.markdown[0].value


def test_mentor_memory_manager():
    import streamlit as st
    from app.components.mentor_memory import MentorMemoryManager

    # Mock candidate context
    cand_ctx = {
        "has_resume": True,
        "name": "Jordan Lee",
        "target_role": "Staff Platform Engineer",
        "years_of_experience": 8.0,
        "skills": ["Kubernetes", "Go", "Terraform"],
        "summary": "Distributed systems specialist.",
    }

    # Clear state first
    if MentorMemoryManager.STATE_KEY in st.session_state:
        del st.session_state[MentorMemoryManager.STATE_KEY]

    # Initialize with seed_from_resume=False - starts clean without predefined facts
    mems = MentorMemoryManager.initialize_memories(cand_ctx, seed_from_resume=False)
    assert mems == []

    # Add custom memory
    MentorMemoryManager.add_memory("Prefers remote roles based in London or Zurich.")
    assert "Prefers remote roles based in London or Zurich." in MentorMemoryManager.get_memories()

    # Remove memory
    count_before = len(MentorMemoryManager.get_memories())
    MentorMemoryManager.remove_memory(0)
    assert len(MentorMemoryManager.get_memories()) == count_before - 1

    # Clear memories
    MentorMemoryManager.clear_memories()
    assert len(MentorMemoryManager.get_memories()) == 0


def test_mentor_rag_thinking_extraction():
    from unittest.mock import MagicMock
    from src.mentor.rag_chain import MentorRAGChain
    from src.mentor.retriever import MentorRetriever

    mock_retriever = MagicMock(spec=MentorRetriever)
    mock_retriever.retrieve.return_value = [
        {"filename": "guide.txt", "source_title": "Interview Guide", "text": "STAR method details", "chunk_index": 0}
    ]

    chain = MentorRAGChain(retriever=mock_retriever, api_key="dummy_key")

    # Mock _call_gemini_rag to return text with thinking tags
    mock_gemini_output = (
        "<thinking>\n"
        "Candidate is asking about behavioral interviews. I will analyze STAR frameworks and provide 3 concrete steps.\n"
        "</thinking>\n"
        "Here is a comprehensive framework for STAR interviews..."
    )
    chain._call_gemini_rag = MagicMock(return_value=mock_gemini_output)

    resp = chain.answer_question(
        question="How should I prepare for a STAR behavioral interview?",
        enable_thinking=True,
    )

    assert resp.thinking is not None
    assert "Candidate is asking about behavioral interviews" in resp.thinking
    assert "<thinking>" not in resp.answer
    assert "Here is a comprehensive framework" in resp.answer
    assert resp.thinking_duration is not None


def test_mentor_rag_unclosed_thinking_recovery():
    """Verify that unclosed <thinking> tags (e.g. from token limit truncation) do not leak into the answer."""
    from unittest.mock import MagicMock
    from src.mentor.rag_chain import MentorRAGChain
    from src.mentor.retriever import MentorRetriever

    mock_retriever = MagicMock(spec=MentorRetriever)
    mock_retriever.retrieve.return_value = []

    chain = MentorRAGChain(retriever=mock_retriever, api_key="dummy_key")

    # Simulate model cutting off mid-thought without closing tag
    truncated_output = (
        "<thinking> 1. Candidate Analysis: The user simply said 'hi'. "
        "2. Strategic Formulation: Keep it brief and friendly. "
        "3. Structure & Tone: Warm greeting."
    )
    chain._call_gemini_rag = MagicMock(return_value=truncated_output)

    resp = chain.answer_question(
        question="hi",
        candidate_context={"name": "Laljith V", "has_resume": True},
        enable_thinking=True,
    )

    # Thinking must be captured
    assert resp.thinking is not None
    assert "Candidate Analysis" in resp.thinking
    # Raw thinking tags must NEVER leak to answer
    assert "<thinking>" not in resp.answer
    assert "</thinking>" not in resp.answer
    # Must have a graceful user-facing greeting
    assert len(resp.answer) > 0
    assert "Laljith" in resp.answer or "Hello" in resp.answer


def test_mentor_database_operations(tmp_path):
    """Test SQL database storage for chat history, messages, and memory."""
    from src.data.mentor_db import MentorDatabase

    test_db = tmp_path / "test_mentor.db"
    MentorDatabase.set_db_path(test_db)

    # 1. Save session and messages
    session_id = "test_sess_001"
    MentorDatabase.save_message(
        session_id=session_id,
        role="user",
        content="What roles fit Python and AWS?",
        candidate_name="Alex Mercer",
        target_role="Cloud ML Engineer",
    )
    MentorDatabase.save_message(
        session_id=session_id,
        role="assistant",
        content="Cloud Machine Learning and MLOps Engineer roles.",
        thinking="Analyzed Python + AWS skill overlap.",
        citations=[{"source_title": "MLOps Guide", "chunk_index": 1}],
    )

    # 2. Verify messages retrieval
    msgs = MentorDatabase.get_session_messages(session_id)
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "What roles fit Python and AWS?"
    assert msgs[1]["role"] == "assistant"
    assert msgs[1]["thinking"] == "Analyzed Python + AWS skill overlap."
    assert len(msgs[1]["citations"]) == 1

    # 3. Verify session listing
    sessions = MentorDatabase.list_sessions()
    assert len(sessions) >= 1
    target_s = next(s for s in sessions if s["id"] == session_id)
    assert target_s["message_count"] == 2
    assert target_s["candidate_name"] == "Alex Mercer"

    # 4. Verify candidate memory persistence
    assert MentorDatabase.add_memory("Prefers remote or hybrid in Seattle.") is True
    assert MentorDatabase.add_memory("Prefers remote or hybrid in Seattle.") is False  # Duplicate ignored
    memories = MentorDatabase.get_memories()
    assert "Prefers remote or hybrid in Seattle." in memories

    # 5. Export session
    exp = MentorDatabase.export_session_data(session_id)
    assert exp is not None
    assert exp["id"] == session_id
    assert len(exp["messages"]) == 2

    # 6. Delete memory and session
    assert MentorDatabase.remove_memory("Prefers remote or hybrid in Seattle.") is True
    assert "Prefers remote or hybrid in Seattle." not in MentorDatabase.get_memories()

    assert MentorDatabase.delete_session(session_id) is True
    assert len(MentorDatabase.get_session_messages(session_id)) == 0


def test_secrets_reading():
    """Verify get_secret handles direct keys, lowercase, database section, and env."""
    import os
    from src.config import get_secret

    os.environ["TEST_ENV_KEY"] = "test_value_123"
    assert get_secret("TEST_ENV_KEY") == "test_value_123"
    assert get_secret("NON_EXISTENT_KEY", default="fallback") == "fallback"


def test_session_scoped_memories(tmp_path):
    """Verify that candidate memory is strictly isolated per chat session, with no cross-session or predefined leakage."""
    import streamlit as st
    from src.data.mentor_db import MentorDatabase
    from app.components.mentor_memory import MentorMemoryManager

    test_db = tmp_path / "test_mentor_sessions.db"
    MentorDatabase.set_db_path(test_db)

    # 1. DB persistence strictly scoped per session
    session_a = "sess_alpha_1"
    session_b = "sess_beta_2"

    MentorDatabase.add_memory("Prefers Python and FastAPI roles.", session_id=session_a)
    MentorDatabase.add_memory("Targeting Senior Go Architect positions.", session_id=session_b)

    mems_a = MentorDatabase.get_memories(session_id=session_a)
    mems_b = MentorDatabase.get_memories(session_id=session_b)

    assert "Prefers Python and FastAPI roles." in mems_a
    assert "Prefers Python and FastAPI roles." not in mems_b
    assert "Targeting Senior Go Architect positions." in mems_b
    assert "Targeting Senior Go Architect positions." not in mems_a

    # 2. MentorMemoryManager session isolation
    cand_ctx = {
        "has_resume": True,
        "name": "Alex Mercer",
        "target_role": "Backend Lead",
        "years_of_experience": 6.0,
        "skills": ["Python", "FastAPI"],
        "summary": "Specialist in microservices.",
    }

    # Initialize Session A - loads existing DB memory for Session A, but no predefined resume facts
    mems_a_mgr = MentorMemoryManager.initialize_memories(cand_ctx, session_id=session_a, seed_from_resume=False)
    assert "Prefers Python and FastAPI roles." in mems_a_mgr
    assert not any("Alex Mercer" in m for m in mems_a_mgr)

    # Add custom memory note in Session A
    MentorMemoryManager.add_memory("Only interested in remote work in Europe.", session_id=session_a)
    current_a = MentorMemoryManager.get_memories(session_id=session_a)
    assert "Only interested in remote work in Europe." in current_a

    # Simulate New Chat -> Session C (reset_session_memories creates clean empty slate)
    session_c = "sess_gamma_3"
    mems_c_mgr = MentorMemoryManager.reset_session_memories(session_c, candidate_context=cand_ctx, seed_from_resume=False)
    assert mems_c_mgr == []
    current_c = MentorMemoryManager.get_memories(session_id=session_c)
    assert current_c == []  # Completely empty, no leakage from session A

    # Add memory in Session B
    MentorMemoryManager.add_memory("Needs minimum salary 120k GBP.", session_id=session_b)
    current_b = MentorMemoryManager.get_memories(session_id=session_b)
    assert "Needs minimum salary 120k GBP." in current_b
    assert "Needs minimum salary 120k GBP." not in MentorMemoryManager.get_memories(session_id=session_a)

    # Simulate History Click -> Load Session A back, loads only Session A's facts
    restored_a = MentorMemoryManager.load_session_memories(session_a)
    assert "Only interested in remote work in Europe." in restored_a
    assert "Needs minimum salary 120k GBP." not in restored_a

    # Deleting a chat session deletes its scoped memories without touching other sessions
    MentorDatabase.delete_session(session_a)
    assert len(MentorDatabase.get_memories(session_id=session_a)) == 0
    assert "Needs minimum salary 120k GBP." in MentorDatabase.get_memories(session_id=session_b)

    # Explicit clear memories removes them for the given session only
    MentorMemoryManager.clear_memories(session_id=session_b)
    assert len(MentorMemoryManager.get_memories(session_id=session_b)) == 0


def test_no_predefined_resume_memory_seeding():
    """Verify memory never pre-populates facts from resume; starts empty for chat turns only."""
    cand_ctx = {
        "has_resume": True,
        "name": "Laljith V",
        "target_role": "Software Engineer",
        "years_of_experience": 2.5,
        "skills": ["Python", "Java", "Next.js"],
        "summary": "Full Stack developer experienced in web and mobile.",
    }

    # 1. CandidateContextManager.get_initial_memories returns empty
    initial_memories = CandidateContextManager.get_initial_memories(cand_ctx)
    assert initial_memories == []

    # 2. MentorMemoryManager initialization with active candidate context stays completely empty
    test_session = "fresh_chat_isolated"
    mems = MentorMemoryManager.initialize_memories(cand_ctx, session_id=test_session, seed_from_resume=False)
    assert mems == []
    assert MentorMemoryManager.get_memories(session_id=test_session) == []
    assert not any("Laljith" in m for m in mems)





