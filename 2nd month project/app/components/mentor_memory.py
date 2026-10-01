"""
Chat-Scoped Memory Manager for SmartHire AI Career Mentor.
Provides conversation-isolated memory that dynamically learns facts discussed
during the active chat alone, strictly preventing leakage across sessions or candidates.
"""

from typing import List, Dict, Any, Optional
import logging
import streamlit as st

from src.mentor.memory_extractor import MentorMemoryExtractor
from src.data.mentor_db import MentorDatabase

logger = logging.getLogger(__name__)


class MentorMemoryManager:
    """Manages conversation memory strictly scoped to the active chat session."""

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
        """Derive session state key based on session ID."""
        s_id = cls._resolve_session_id(session_id)
        if s_id:
            return f"{cls.STATE_KEY_PREFIX}{s_id}"
        return cls.STATE_KEY

    @classmethod
    def initialize_memories(
        cls,
        candidate_ctx: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        seed_from_resume: bool = False,
    ) -> List[str]:
        """
        Initialize memories strictly for the active chat session.
        No predefined resume facts are injected. Memories are learned dynamically
        from what was discussed during the conversation, or from custom notes.
        """
        s_id = cls._resolve_session_id(session_id)
        state_key = cls._get_state_key(s_id)

        # 1. Load memories already persisted for this session from database
        if s_id:
            try:
                persisted = MentorDatabase.get_memories(session_id=s_id)
                if persisted:
                    st.session_state[state_key] = list(persisted)
                    st.session_state[cls.STATE_KEY] = list(persisted)
                    return st.session_state[state_key]
            except Exception as exc:
                logger.warning(f"Could not load memories from database for session {s_id}: {exc}")

        # 2. Check if already in session state for this session
        if state_key in st.session_state and st.session_state[state_key] is not None:
            mems = st.session_state[state_key]
            st.session_state[cls.STATE_KEY] = mems
            return mems

        # Fresh chat: starts completely empty for this chat alone
        st.session_state[state_key] = []
        st.session_state[cls.STATE_KEY] = []
        return []

    @classmethod
    def get_memories(cls, session_id: Optional[str] = None) -> List[str]:
        """Return the active memories strictly for the specified chat session."""
        s_id = cls._resolve_session_id(session_id)
        state_key = cls._get_state_key(s_id)

        if state_key in st.session_state and st.session_state[state_key] is not None:
            return st.session_state[state_key]

        try:
            db_mems = MentorDatabase.get_memories(session_id=s_id)
            st.session_state[state_key] = list(db_mems)
            st.session_state[cls.STATE_KEY] = list(db_mems)
            return st.session_state[state_key]
        except Exception:
            return []

    @classmethod
    def add_memory(cls, memory_text: str, session_id: Optional[str] = None) -> None:
        """Add a new memory fact strictly to this chat session and database."""
        clean_text = memory_text.strip()
        if not clean_text:
            return

        s_id = cls._resolve_session_id(session_id)
        state_key = cls._get_state_key(s_id)
        mems = cls.get_memories(s_id)
        if clean_text not in mems:
            mems.append(clean_text)
            st.session_state[state_key] = mems
            st.session_state[cls.STATE_KEY] = mems

        try:
            MentorDatabase.add_memory(clean_text, session_id=s_id)
        except Exception as exc:
            logger.warning(f"Could not save memory to database: {exc}")

    @classmethod
    def reset_session_memories(
        cls,
        new_session_id: str,
        candidate_ctx: Optional[Dict[str, Any]] = None,
        candidate_context: Optional[Dict[str, Any]] = None,
        seed_from_resume: bool = False,
    ) -> List[str]:
        """
        Called when starting a '+ New chat'.
        Initializes a fresh, empty memory state for the new session, strictly isolated from other chats.
        """
        state_key = cls._get_state_key(new_session_id)
        st.session_state[state_key] = []
        st.session_state[cls.STATE_KEY] = []
        return []

    @classmethod
    def load_session_memories(cls, session_id: str) -> List[str]:
        """
        Called when restoring a conversation from History.
        Loads that specific chat's memories alone from database.
        """
        state_key = cls._get_state_key(session_id)
        try:
            db_mems = MentorDatabase.get_memories(session_id=session_id)
        except Exception as exc:
            logger.warning(f"Could not load memories for session {session_id}: {exc}")
            db_mems = []

        st.session_state[state_key] = list(db_mems)
        st.session_state[cls.STATE_KEY] = list(db_mems)
        return st.session_state[state_key]

    @classmethod
    def remove_memory(cls, index: int, session_id: Optional[str] = None) -> None:
        """Remove a memory by index from this chat session."""
        s_id = cls._resolve_session_id(session_id)
        state_key = cls._get_state_key(s_id)
        mems = cls.get_memories(s_id)
        if 0 <= index < len(mems):
            removed_fact = mems.pop(index)
            st.session_state[state_key] = mems
            st.session_state[cls.STATE_KEY] = mems
            try:
                MentorDatabase.remove_memory(removed_fact, session_id=s_id)
            except Exception as exc:
                logger.warning(f"Could not remove memory from database: {exc}")

    @classmethod
    def clear_memories(cls, session_id: Optional[str] = None) -> None:
        """Clear memories strictly for this chat session."""
        s_id = cls._resolve_session_id(session_id)
        state_key = cls._get_state_key(s_id)
        st.session_state[state_key] = []
        st.session_state[cls.STATE_KEY] = []
        try:
            MentorDatabase.clear_memories(session_id=s_id)
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
        Autonomously inspect what was discussed in THIS chat turn, extract new facts,
        and add them to this chat's active memories alone.
        """
        s_id = cls._resolve_session_id(session_id)
        existing = cls.get_memories(s_id)
        new_facts = MentorMemoryExtractor.extract_new_facts(
            user_text=user_text,
            assistant_text=assistant_text,
            existing_memories=existing,
            api_key=api_key,
        )
        added: List[str] = []
        for fact in new_facts:
            if fact not in cls.get_memories(s_id):
                cls.add_memory(fact, session_id=s_id)
                added.append(fact)

        if added:
            logger.info(f"Autonomously extracted {len(added)} new candidate memories for chat {s_id}: {added}")
        return added

    @classmethod
    def sync_from_indexeddb(cls, db_memories: List[Dict[str, Any]], session_id: Optional[str] = None) -> None:
        """Compatibility helper for migrating or syncing memories."""
        if not db_memories:
            return
        s_id = cls._resolve_session_id(session_id)
        for item in db_memories:
            fact = item.get("fact") or item.get("text")
            if fact:
                cls.add_memory(fact, session_id=s_id)


__all__ = ["MentorMemoryManager"]

