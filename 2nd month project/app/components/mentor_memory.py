"""
Persistent Candidate Memory Manager for SmartHire AI Career Mentor.
Provides long-term memory for candidate preferences, strengths, career goals,
and target roles, persisted reliably in SQL database storage across conversations.
"""

from typing import List, Dict, Any, Optional
import logging
import streamlit as st

from src.mentor.candidate_context import CandidateContextManager
from src.mentor.memory_extractor import MentorMemoryExtractor
from src.data.mentor_db import MentorDatabase

logger = logging.getLogger(__name__)


class MentorMemoryManager:
    """Manages candidate memory bank persisted across conversations in SQL database."""

    STATE_KEY = "mentor_candidate_memories"
    STATE_KEY_PREFIX = "mentor_candidate_memories_"

    @classmethod
    def _resolve_session_id(cls, session_id: Optional[str] = None) -> Optional[str]:
        """Resolve the session ID from argument or active Streamlit session state."""
        if session_id:
            return session_id
        if hasattr(st, "session_state") and "mentor_session_id" in st.session_state:
            return st.session_state.mentor_session_id
        return None

    @classmethod
    def _get_state_key(cls, session_id: Optional[str] = None) -> str:
        """Derive session state key."""
        return cls.STATE_KEY

    @classmethod
    def initialize_memories(
        cls,
        candidate_ctx: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        seed_from_resume: bool = True,
    ) -> List[str]:
        """
        Initialize candidate memories across chats.
        1. Checks SQLite database first for persistent candidate memories.
        2. If empty and candidate has a profile/resume, auto-seeds core facts
           (name, target role, experience, skills, bio summary) to DB and session state.
        3. Returns all active candidate memories.
        """
        # 1. Load existing memories from database
        try:
            persisted_mems = MentorDatabase.get_memories()
            if persisted_mems:
                st.session_state[cls.STATE_KEY] = list(persisted_mems)
        except Exception as exc:
            logger.warning(f"Could not load memories from database: {exc}")

        if cls.STATE_KEY not in st.session_state or st.session_state[cls.STATE_KEY] is None:
            st.session_state[cls.STATE_KEY] = []

        # 2. If candidate resume/profile is available, ensure core profile facts are seeded
        if seed_from_resume and candidate_ctx and candidate_ctx.get("has_resume"):
            initial = CandidateContextManager.get_initial_memories(candidate_ctx)
            current = st.session_state[cls.STATE_KEY]
            for fact in initial:
                if fact not in current:
                    current.append(fact)
                    try:
                        MentorDatabase.add_memory(fact, session_id=session_id)
                    except Exception as exc:
                        logger.warning(f"Could not persist initial memory to database: {exc}")
            st.session_state[cls.STATE_KEY] = current

        return st.session_state[cls.STATE_KEY]

    @classmethod
    def get_memories(cls, session_id: Optional[str] = None) -> List[str]:
        """Return the active candidate memories bank across conversations."""
        if cls.STATE_KEY in st.session_state and st.session_state[cls.STATE_KEY] is not None:
            return st.session_state[cls.STATE_KEY]
        try:
            db_mems = MentorDatabase.get_memories()
            st.session_state[cls.STATE_KEY] = list(db_mems)
            return st.session_state[cls.STATE_KEY]
        except Exception:
            return []

    @classmethod
    def add_memory(cls, memory_text: str, session_id: Optional[str] = None) -> None:
        """Add a new candidate memory fact and persist to database and session state."""
        clean_text = memory_text.strip()
        if not clean_text:
            return

        mems = cls.get_memories(session_id)
        if clean_text not in mems:
            mems.append(clean_text)
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
        seed_from_resume: bool = True,
    ) -> List[str]:
        """
        Called when starting a '+ New chat'.
        Preserves candidate memory bank across chats so past memories remain accessible
        in the new conversation, while seeding from resume if memories were empty.
        """
        ctx = candidate_context if candidate_context is not None else (candidate_ctx or {})
        return cls.initialize_memories(candidate_ctx=ctx, session_id=new_session_id, seed_from_resume=seed_from_resume)

    @classmethod
    def load_session_memories(cls, session_id: str) -> List[str]:
        """
        Called when restoring a conversation from History.
        Loads all persistent candidate memories so they remain active.
        """
        return cls.get_memories(session_id=session_id)

    @classmethod
    def remove_memory(cls, index: int, session_id: Optional[str] = None) -> None:
        """Remove a memory by index from session state and database."""
        mems = cls.get_memories(session_id)
        if 0 <= index < len(mems):
            removed_fact = mems.pop(index)
            st.session_state[cls.STATE_KEY] = mems
            try:
                MentorDatabase.remove_memory(removed_fact, session_id=session_id)
            except Exception as exc:
                logger.warning(f"Could not remove memory from database: {exc}")

    @classmethod
    def clear_memories(cls, session_id: Optional[str] = None) -> None:
        """Clear candidate memories from state and database."""
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
        add them to candidate memories and database, and return newly discovered facts.
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
            logger.info(f"Autonomously extracted {len(added)} new candidate memories: {added}")
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

