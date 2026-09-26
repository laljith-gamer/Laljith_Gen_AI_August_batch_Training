"""
Persistent Candidate Memory Manager for SmartHire AI Career Mentor.
Provides ChatGPT-style long-term memory for candidate preferences, strengths,
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
    """Manages persistent candidate memory across sessions backed by SQL database."""

    STATE_KEY = "mentor_candidate_memories"

    @classmethod
    def initialize_memories(cls, candidate_ctx: Dict[str, Any]) -> List[str]:
        """Initialize memories from database or extract from candidate context."""
        # Check database first
        try:
            persisted_mems = MentorDatabase.get_memories()
        except Exception as exc:
            logger.warning(f"Could not load memories from database: {exc}")
            persisted_mems = []

        if persisted_mems:
            st.session_state[cls.STATE_KEY] = persisted_mems
            return persisted_mems

        if cls.STATE_KEY not in st.session_state:
            initial = CandidateContextManager.get_initial_memories(candidate_ctx)
            st.session_state[cls.STATE_KEY] = initial
            # Persist initial memories into database
            for fact in initial:
                try:
                    MentorDatabase.add_memory(fact)
                except Exception as exc:
                    logger.warning(f"Could not persist initial memory to database: {exc}")

        return st.session_state.get(cls.STATE_KEY, [])

    @classmethod
    def get_memories(cls) -> List[str]:
        """Return the current active memories."""
        if cls.STATE_KEY in st.session_state:
            return st.session_state[cls.STATE_KEY]
        try:
            db_mems = MentorDatabase.get_memories()
            st.session_state[cls.STATE_KEY] = db_mems
            return db_mems
        except Exception:
            return []

    @classmethod
    def add_memory(cls, memory_text: str) -> None:
        """Add a new memory fact and persist to database."""
        clean_text = memory_text.strip()
        if not clean_text:
            return
        mems = cls.get_memories()
        if clean_text not in mems:
            mems.append(clean_text)
            st.session_state[cls.STATE_KEY] = mems

        try:
            MentorDatabase.add_memory(clean_text)
        except Exception as exc:
            logger.warning(f"Could not save memory to database: {exc}")

    @classmethod
    def process_turn_autonomously(
        cls,
        user_text: str,
        assistant_text: str,
        api_key: Optional[str] = None,
    ) -> List[str]:
        """
        Autonomously inspect a chat interaction turn, extract new candidate facts,
        add them to active session memories and database, and return the newly discovered facts.
        """
        existing = cls.get_memories()
        new_facts = MentorMemoryExtractor.extract_new_facts(
            user_text=user_text,
            assistant_text=assistant_text,
            existing_memories=existing,
            api_key=api_key,
        )
        added: List[str] = []
        for fact in new_facts:
            if fact not in cls.get_memories():
                cls.add_memory(fact)
                added.append(fact)

        if added:
            logger.info(f"Autonomously extracted {len(added)} new candidate memories: {added}")
        return added

    @classmethod
    def remove_memory(cls, index: int) -> None:
        """Remove a memory by index and delete from database."""
        mems = cls.get_memories()
        if 0 <= index < len(mems):
            removed_fact = mems.pop(index)
            st.session_state[cls.STATE_KEY] = mems
            try:
                MentorDatabase.remove_memory(removed_fact)
            except Exception as exc:
                logger.warning(f"Could not remove memory from database: {exc}")

    @classmethod
    def clear_memories(cls) -> None:
        """Clear all active memories from session state and database."""
        st.session_state[cls.STATE_KEY] = []
        try:
            MentorDatabase.clear_memories()
        except Exception as exc:
            logger.warning(f"Could not clear memories from database: {exc}")

    @classmethod
    def sync_from_indexeddb(cls, db_memories: List[Dict[str, Any]]) -> None:
        """Compatibility helper for migrating or syncing memories."""
        if not db_memories:
            return
        for item in db_memories:
            fact = item.get("fact") or item.get("text")
            if fact:
                cls.add_memory(fact)


__all__ = ["MentorMemoryManager"]
