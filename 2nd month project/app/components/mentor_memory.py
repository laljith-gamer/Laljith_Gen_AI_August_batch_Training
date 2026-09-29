"""
Persistent Candidate Memory Manager for SmartHire AI Career Mentor.
Provides session-scoped long-term memory for candidate preferences, strengths,
career goals, and target roles, persisted reliably in SQL database storage.
"""

from typing import List, Dict, Any, Optional
import logging
import streamlit as st

from src.mentor.candidate_context import CandidateContextManager
from src.mentor.memory_extractor import MentorMemoryExtractor
from src.data.mentor_db import MentorDatabase

logger = logging.getLogger(__name__)


class MentorMemoryManager:
    """Manages candidate memory scoped per chat session and backed by SQL database."""

    STATE_KEY = "mentor_candidate_memories"
    STATE_KEY_PREFIX = "mentor_candidate_memories_"

    @classmethod
    def _get_state_key(cls, session_id: Optional[str] = None) -> str:
        """Derive session state key based on session ID."""
        if session_id:
            return f"{cls.STATE_KEY_PREFIX}{session_id}"
        return cls.STATE_KEY

    @classmethod
    def initialize_memories(
        cls,
        candidate_ctx: Dict[str, Any],
        session_id: Optional[str] = None,
    ) -> List[str]:
        """
        Initialize memories for a specific session.
        Checks database for existing memories for this session.
        If empty and candidate has a resume, populates initial base facts for this session.
        """
        state_key = cls._get_state_key(session_id)

        # 1. Check database first for memories saved to this session
        try:
            persisted_mems = MentorDatabase.get_memories(session_id=session_id)
        except Exception as exc:
            logger.warning(f"Could not load memories from database for session {session_id}: {exc}")
            persisted_mems = []

        if persisted_mems:
            st.session_state[state_key] = persisted_mems
            st.session_state[cls.STATE_KEY] = persisted_mems
            return persisted_mems

        # 2. Check if already initialized in session state
        if state_key in st.session_state and st.session_state[state_key]:
            mems = st.session_state[state_key]
            st.session_state[cls.STATE_KEY] = mems
            return mems

        # 3. Fresh session: initialize base facts from resume context if available
        if candidate_ctx.get("has_resume"):
            initial = CandidateContextManager.get_initial_memories(candidate_ctx)
            st.session_state[state_key] = initial
            st.session_state[cls.STATE_KEY] = initial
            for fact in initial:
                try:
                    MentorDatabase.add_memory(fact, session_id=session_id)
                except Exception as exc:
                    logger.warning(f"Could not persist initial memory to database: {exc}")
            return initial

        # No resume: start completely fresh
        st.session_state[state_key] = []
        st.session_state[cls.STATE_KEY] = []
        return []

    @classmethod
    def get_memories(cls, session_id: Optional[str] = None) -> List[str]:
        """Return the active memories for a given session."""
        state_key = cls._get_state_key(session_id)
        if state_key in st.session_state:
            return st.session_state[state_key]
        try:
            db_mems = MentorDatabase.get_memories(session_id=session_id)
            st.session_state[state_key] = db_mems
            st.session_state[cls.STATE_KEY] = db_mems
            return db_mems
        except Exception:
            return []

    @classmethod
    def add_memory(cls, memory_text: str, session_id: Optional[str] = None) -> None:
        """Add a new memory fact to the specified session and persist to database."""
        clean_text = memory_text.strip()
        if not clean_text:
            return
        state_key = cls._get_state_key(session_id)
        mems = cls.get_memories(session_id)
        if clean_text not in mems:
            mems.append(clean_text)
            st.session_state[state_key] = mems
            st.session_state[cls.STATE_KEY] = mems

        try:
            MentorDatabase.add_memory(clean_text, session_id=session_id)
        except Exception as exc:
            logger.warning(f"Could not save memory to database: {exc}")

    @classmethod
    def reset_session_memories(
        cls,
        new_session_id: str,
        candidate_ctx: Optional[Dict[str, Any]] = None,
        candidate_context: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        Called when starting a '+ New chat'.
        Initializes fresh base memories for the new session without previous chat pollution.
        """
        ctx = candidate_context if candidate_context is not None else (candidate_ctx or {})
        state_key = cls._get_state_key(new_session_id)
        if ctx.get("has_resume"):
            initial = CandidateContextManager.get_initial_memories(ctx)
            st.session_state[state_key] = initial
            st.session_state[cls.STATE_KEY] = initial
            for fact in initial:
                try:
                    MentorDatabase.add_memory(fact, session_id=new_session_id)
                except Exception as exc:
                    logger.warning(f"Could not persist initial memory: {exc}")
            return initial
        else:
            st.session_state[state_key] = []
            st.session_state[cls.STATE_KEY] = []
            return []

    @classmethod
    def load_session_memories(cls, session_id: str) -> List[str]:
        """
        Called when restoring a conversation from History.
        Loads that specific session's memories from database into session state.
        """
        state_key = cls._get_state_key(session_id)
        try:
            db_mems = MentorDatabase.get_memories(session_id=session_id)
        except Exception as exc:
            logger.warning(f"Could not load memories for session {session_id}: {exc}")
            db_mems = []
        st.session_state[state_key] = db_mems
        st.session_state[cls.STATE_KEY] = db_mems
        return db_mems

    @classmethod
    def remove_memory(cls, index: int, session_id: Optional[str] = None) -> None:
        """Remove a memory by index from the specified session."""
        state_key = cls._get_state_key(session_id)
        mems = cls.get_memories(session_id)
        if 0 <= index < len(mems):
            removed_fact = mems.pop(index)
            st.session_state[state_key] = mems
            st.session_state[cls.STATE_KEY] = mems
            try:
                MentorDatabase.remove_memory(removed_fact, session_id=session_id)
            except Exception as exc:
                logger.warning(f"Could not remove memory from database: {exc}")

    @classmethod
    def clear_memories(cls, session_id: Optional[str] = None) -> None:
        """Clear memories for the specified session from state and database."""
        state_key = cls._get_state_key(session_id)
        st.session_state[state_key] = []
        st.session_state[cls.STATE_KEY] = []
        try:
            MentorDatabase.clear_memories(session_id=session_id)
        except Exception as exc:
            logger.warning(f"Could not clear memories from database: {exc}")

    @classmethod
    def process_turn_autonomously(
        cls,
        user_text: str,
        assistant_text: str,
        session_id: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> List[str]:
        """
        Autonomously inspect a chat interaction turn, extract new candidate facts,
        add them to the session's active memories and database, and return newly discovered facts.
        """
        existing = cls.get_memories(session_id)
        new_facts = MentorMemoryExtractor.extract_new_facts(
            user_text=user_text,
            assistant_text=assistant_text,
            existing_memories=existing,
            api_key=api_key,
        )
        added: List[str] = []
        for fact in new_facts:
            if fact not in cls.get_memories(session_id):
                cls.add_memory(fact, session_id=session_id)
                added.append(fact)

        if added:
            logger.info(f"Autonomously extracted {len(added)} new candidate memories for session {session_id}: {added}")
        return added

    @classmethod
    def sync_from_indexeddb(cls, db_memories: List[Dict[str, Any]], session_id: Optional[str] = None) -> None:
        """Compatibility helper for migrating or syncing memories."""
        if not db_memories:
            return
        for item in db_memories:
            fact = item.get("fact") or item.get("text")
            if fact:
                cls.add_memory(fact, session_id=session_id)


__all__ = ["MentorMemoryManager"]
