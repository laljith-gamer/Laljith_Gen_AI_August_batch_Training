"""
Persistent Candidate Memory Manager for SmartHire AI Career Mentor.
Provides ChatGPT-style long-term memory for candidate preferences, strengths,
career goals, and target roles, persisted in browser IndexedDB.
"""

from typing import List, Dict, Any, Optional
import time
import logging
import streamlit as st

from src.mentor.candidate_context import CandidateContextManager
from src.mentor.memory_extractor import MentorMemoryExtractor

logger = logging.getLogger(__name__)


class MentorMemoryManager:
    """Manages persistent candidate memory across sessions."""

    STATE_KEY = "mentor_candidate_memories"

    @classmethod
    def initialize_memories(cls, candidate_ctx: Dict[str, Any]) -> List[str]:
        """Initialize memories from candidate context if not already loaded."""
        if cls.STATE_KEY not in st.session_state:
            initial = CandidateContextManager.get_initial_memories(candidate_ctx)
            st.session_state[cls.STATE_KEY] = initial
        return st.session_state[cls.STATE_KEY]

    @classmethod
    def get_memories(cls) -> List[str]:
        """Return the current active memories."""
        return st.session_state.get(cls.STATE_KEY, [])

    @classmethod
    def add_memory(cls, memory_text: str) -> None:
        """Add a new memory fact."""
        clean_text = memory_text.strip()
        if not clean_text:
            return
        mems = cls.get_memories()
        if clean_text not in mems:
            mems.append(clean_text)
            st.session_state[cls.STATE_KEY] = mems

    @classmethod
    def process_turn_autonomously(
        cls,
        user_text: str,
        assistant_text: str,
        api_key: Optional[str] = None,
    ) -> List[str]:
        """
        Autonomously inspect a chat interaction turn, extract new candidate facts,
        add them to active session memories, and return the newly discovered facts.
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
        """Remove a memory by index."""
        mems = cls.get_memories()
        if 0 <= index < len(mems):
            mems.pop(index)
            st.session_state[cls.STATE_KEY] = mems

    @classmethod
    def clear_memories(cls) -> None:
        """Clear all active memories."""
        st.session_state[cls.STATE_KEY] = []

    @classmethod
    def sync_from_indexeddb(cls, db_memories: List[Dict[str, Any]]) -> None:
        """Merge memories retrieved from browser IndexedDB."""
        if not db_memories:
            return
        current = set(cls.get_memories())
        for item in db_memories:
            fact = item.get("fact") or item.get("text")
            if fact and fact not in current:
                current.add(fact)
        st.session_state[cls.STATE_KEY] = list(current)

