"""
Database Storage Engine for SmartHire AI Career Mentor.
Replaces browser-side IndexedDB with a persistent, server-side SQL database (SQLite
by default, configurable via Streamlit Cloud Secrets / st.secrets).

Persists:
- Multi-turn conversation sessions and message history
- Thinking process reasoning and document citations
- Candidate memory facts
"""

import json
import logging
from typing import Dict, Any, List, Optional
import streamlit as st

from src.data.mentor_db import MentorDatabase

logger = logging.getLogger(__name__)


class MentorDatabaseManager:
    """High-level database management for Career Mentor conversations and memory."""

    @classmethod
    def get_database(cls) -> type[MentorDatabase]:
        return MentorDatabase

    @classmethod
    def save_message(
        cls,
        session_id: str,
        role: str,
        content: str,
        thinking: Optional[str] = None,
        citations: Optional[List[Dict[str, Any]]] = None,
        candidate_name: str = "Candidate",
        target_role: str = "Engineering / Tech",
    ) -> None:
        """Persist a single chat message to the database."""
        try:
            MentorDatabase.save_message(
                session_id=session_id,
                role=role,
                content=content,
                thinking=thinking,
                citations=citations,
                candidate_name=candidate_name,
                target_role=target_role,
            )
        except Exception as exc:
            logger.error(f"Failed to save message to database: {exc}", exc_info=True)

    @classmethod
    def load_session(cls, session_id: str) -> List[Dict[str, Any]]:
        """Load full message history for a given session."""
        try:
            return MentorDatabase.get_session_messages(session_id)
        except Exception as exc:
            logger.error(f"Failed to load session {session_id} from database: {exc}", exc_info=True)
            return []

    @classmethod
    def list_sessions(cls) -> List[Dict[str, Any]]:
        """List all saved sessions ordered by last update."""
        try:
            return MentorDatabase.list_sessions()
        except Exception as exc:
            logger.error(f"Failed to list sessions from database: {exc}", exc_info=True)
            return []

    @classmethod
    def delete_session(cls, session_id: str) -> bool:
        """Delete a conversation session."""
        try:
            return MentorDatabase.delete_session(session_id)
        except Exception as exc:
            logger.error(f"Failed to delete session {session_id}: {exc}", exc_info=True)
            return False

    @classmethod
    def clear_all_sessions(cls) -> bool:
        """Clear all saved chat history."""
        try:
            return MentorDatabase.clear_all_sessions()
        except Exception as exc:
            logger.error(f"Failed to clear sessions: {exc}", exc_info=True)
            return False

    @classmethod
    def export_session_json(cls, session_id: str) -> str:
        """Export session data formatted as JSON."""
        data = MentorDatabase.export_session_data(session_id)
        return json.dumps(data, indent=2, default=str) if data else "{}"

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """Return database telemetry and health status."""
        return MentorDatabase.get_status()


class MentorIndexedDBManager:
    """
    Backward-compatible adapter that proxies legacy IndexedDB calls directly to
    the SQL database storage engine.
    """

    @classmethod
    def render_storage_toolbar(
        cls,
        active_session_id: str,
        messages: List[Dict[str, Any]],
        candidate_summary: Dict[str, Any],
        action_override: Optional[str] = None,
        action_payload: Optional[Dict[str, Any]] = None,
        key: str = "mentor_idb_sync",
    ) -> Optional[Any]:
        """
        Adapter method preserving previous signature. Syncs current conversation
        directly to SQL database storage.
        """
        if messages and len(messages) > 0:
            name = candidate_summary.get("name", "Candidate")
            role = candidate_summary.get("target_role", "Engineering / Tech")
            # Ensure latest message is stored
            last_msg = messages[-1]
            MentorDatabase.save_message(
                session_id=active_session_id,
                role=last_msg.get("role", "user"),
                content=last_msg.get("content", ""),
                thinking=last_msg.get("thinking"),
                citations=last_msg.get("citations"),
                candidate_name=name,
                target_role=role,
            )

        # Return a lightweight shim object compatible with any legacy attribute checks
        class _StorageResultShim:
            restore_session_payload = None
            cleared_storage_trigger = None
            saved_sessions = MentorDatabase.list_sessions()
            stored_memories = [
                {"fact": m, "key": f"mem_{i}"}
                for i, m in enumerate(MentorDatabase.get_memories())
            ]

        return _StorageResultShim()


__all__ = ["MentorDatabaseManager", "MentorIndexedDBManager", "MentorDatabase"]
