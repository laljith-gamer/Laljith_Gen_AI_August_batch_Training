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
    def _recover_memories_for_session(
        cls,
        session_id: str,
        messages: Optional[List[Dict[str, Any]]] = None,
    ) -> List[str]:
        """
        Recovers and persists memories for an existing chat session that has no memories recorded in DB yet.
        Only runs for sessions that actually exist in the database with records or messages.
        Brand new empty sessions return [] immediately.
        """
        try:
            sess_meta = MentorDatabase.get_session(session_id)
        except Exception:
            sess_meta = None

        chat_msgs = messages
        if chat_msgs is None:
            try:
                chat_msgs = MentorDatabase.get_session_messages(session_id)
            except Exception:
                chat_msgs = []

        # If this is a fresh new session without DB records or messages, do not recover anything
        if not sess_meta and not chat_msgs:
            return []

        recovered: List[str] = []

        # 1. Check if there are legacy unscoped memories in DB (pre-session-isolation versions)
        try:
            unscoped = MentorDatabase.get_memories(session_id=None)
            if unscoped:
                for fact in unscoped:
                    clean = fact.strip()
                    if clean and clean not in recovered:
                        recovered.append(clean)
                        MentorDatabase.add_memory(clean, session_id=session_id)
        except Exception as exc:
            logger.debug(f"Unscoped memory check: {exc}")

        # 2. Check session metadata in mentor_sessions
        if sess_meta:
            c_name = sess_meta.get("candidate_name")
            c_role = sess_meta.get("target_role")
            if c_name and c_name != "Candidate" and not any(c_name.lower() in r.lower() for r in recovered):
                fact = f"Candidate name: {c_name}"
                recovered.append(fact)
                MentorDatabase.add_memory(fact, session_id=session_id)
            if c_role and "Engineering / Tech" not in c_role and not any("target role" in r.lower() for r in recovered):
                fact = f"Target role: {c_role}"
                recovered.append(fact)
                MentorDatabase.add_memory(fact, session_id=session_id)

        # 3. Extract facts discussed in this session's past messages
        if chat_msgs:
            for msg in chat_msgs:
                if msg.get("role") == "user":
                    text = str(msg.get("content", ""))
                    if len(text.strip()) >= 4:
                        turn_facts = MentorMemoryExtractor._extract_pattern_facts(text, recovered)
                        for f in turn_facts:
                            clean = f.strip()
                            if clean and clean not in recovered:
                                recovered.append(clean)
                                MentorDatabase.add_memory(clean, session_id=session_id)

        return recovered

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

        # 2. Check if already in session state for this session (and has facts)
        if state_key in st.session_state and st.session_state[state_key]:
            mems = st.session_state[state_key]
            st.session_state[cls.STATE_KEY] = mems
            return mems

        # 3. If an existing session has messages in DB, recover its memories
        if s_id:
            recovered = cls._recover_memories_for_session(s_id)
            if recovered:
                st.session_state[state_key] = list(recovered)
                st.session_state[cls.STATE_KEY] = list(recovered)
                return st.session_state[state_key]

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
    def load_session_memories(
        cls,
        session_id: str,
        messages: Optional[List[Dict[str, Any]]] = None,
    ) -> List[str]:
        """
        Called when restoring a conversation from History.
        Loads that specific chat's memories alone from database.
        If this chat has no recorded memories in DB yet, automatically recovers memories
        from this chat's recorded messages, session metadata, or legacy unscoped records.
        """
        state_key = cls._get_state_key(session_id)
        db_mems: List[str] = []
        try:
            db_mems = MentorDatabase.get_memories(session_id=session_id)
        except Exception as exc:
            logger.warning(f"Could not load memories for session {session_id}: {exc}")

        # If this session has no recorded memories in DB yet, attempt recovery:
        if not db_mems:
            db_mems = cls._recover_memories_for_session(session_id, messages=messages)

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

