"""
Database storage engine for SmartHire Career Mentor.
Persists multi-turn conversations, chat history, and candidate memory into a reliable
SQL database (SQLite by default, configurable via Streamlit Secrets or environment variables).
"""

import sqlite3
import json
import time
import datetime
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class MentorDatabase:
    """Manages persistent SQL database operations for Career Mentor chat and memory."""

    _db_path: Optional[Path] = None

    @classmethod
    def get_db_path(cls) -> Path:
        """Resolve database path from settings or default to data/mentor_history.db."""
        if cls._db_path is not None:
            return cls._db_path

        from src.config import settings
        cls._db_path = getattr(settings, "DB_PATH", settings.PROJECT_ROOT / "data/mentor_history.db")
        cls._db_path.parent.mkdir(parents=True, exist_ok=True)
        return cls._db_path

    @classmethod
    def set_db_path(cls, path: Path) -> None:
        """Override database path (useful for testing)."""
        cls._db_path = path
        cls._db_path.parent.mkdir(parents=True, exist_ok=True)
        cls.init_db()

    @classmethod
    def _get_connection(cls) -> sqlite3.Connection:
        """Create a connection with WAL mode and row factory enabled."""
        db_file = cls.get_db_path()
        conn = sqlite3.connect(str(db_file), timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    @classmethod
    def init_db(cls) -> None:
        """Initialize database schema if tables do not exist."""
        with cls._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS mentor_sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                candidate_name TEXT DEFAULT 'Candidate',
                target_role TEXT DEFAULT 'Engineering / Tech',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS mentor_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                thinking TEXT,
                citations_json TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES mentor_sessions(id) ON DELETE CASCADE
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS mentor_memories (
                key TEXT PRIMARY KEY,
                fact TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON mentor_messages(session_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_updated ON mentor_sessions(updated_at DESC);")
            conn.commit()

    # --- CHAT SESSION MANAGEMENT ---

    @classmethod
    def save_session(
        cls,
        session_id: str,
        title: str,
        candidate_name: str = "Candidate",
        target_role: str = "Engineering / Tech",
    ) -> None:
        """Create or update a conversation session record."""
        cls.init_db()
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with cls._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM mentor_sessions WHERE id = ?;", (session_id,))
            exists = cursor.fetchone() is not None

            if exists:
                cursor.execute("""
                    UPDATE mentor_sessions
                    SET title = ?, candidate_name = ?, target_role = ?, updated_at = ?
                    WHERE id = ?;
                """, (title, candidate_name, target_role, now_iso, session_id))
            else:
                cursor.execute("""
                    INSERT INTO mentor_sessions (id, title, candidate_name, target_role, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?);
                """, (session_id, title, candidate_name, target_role, now_iso, now_iso))
            conn.commit()

    @classmethod
    def list_sessions(cls) -> List[Dict[str, Any]]:
        """List all saved chat sessions ordered by most recently updated."""
        cls.init_db()
        with cls._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.id, s.title, s.candidate_name, s.target_role, s.created_at, s.updated_at,
                       COUNT(m.id) AS message_count
                FROM mentor_sessions s
                LEFT JOIN mentor_messages m ON s.id = m.session_id
                GROUP BY s.id
                ORDER BY s.updated_at DESC;
            """)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    @classmethod
    def delete_session(cls, session_id: str) -> bool:
        """Delete a chat session and all its associated messages."""
        cls.init_db()
        with cls._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM mentor_messages WHERE session_id = ?;", (session_id,))
            cursor.execute("DELETE FROM mentor_sessions WHERE id = ?;", (session_id,))
            conn.commit()
            return cursor.rowcount > 0

    @classmethod
    def clear_all_sessions(cls) -> bool:
        """Delete all chat sessions and messages."""
        cls.init_db()
        with cls._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM mentor_messages;")
            cursor.execute("DELETE FROM mentor_sessions;")
            conn.commit()
            return True

    # --- MESSAGE MANAGEMENT ---

    @classmethod
    def save_message(
        cls,
        session_id: str,
        role: str,
        content: str,
        thinking: Optional[str] = None,
        citations: Optional[List[Dict[str, Any]]] = None,
        timestamp: Optional[str] = None,
        candidate_name: str = "Candidate",
        target_role: str = "Engineering / Tech",
    ) -> None:
        """Save a message to the database and update session timestamp."""
        cls.init_db()
        ts = timestamp or datetime.datetime.now(datetime.timezone.utc).isoformat()
        citations_json = json.dumps(citations) if citations else None

        with cls._get_connection() as conn:
            cursor = conn.cursor()

            # Ensure session exists
            cursor.execute("SELECT id, title FROM mentor_sessions WHERE id = ?;", (session_id,))
            row = cursor.fetchone()
            if not row:
                title = (content[:45] + "...") if len(content) > 45 else (content.strip() or "Career Mentoring")
                cursor.execute("""
                    INSERT INTO mentor_sessions (id, title, candidate_name, target_role, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?);
                """, (session_id, title, candidate_name, target_role, ts, ts))
            else:
                cursor.execute("UPDATE mentor_sessions SET updated_at = ? WHERE id = ?;", (ts, session_id))

            cursor.execute("""
                INSERT INTO mentor_messages (session_id, role, content, thinking, citations_json, timestamp)
                VALUES (?, ?, ?, ?, ?, ?);
            """, (session_id, role, content, thinking, citations_json, ts))
            conn.commit()

    @classmethod
    def get_session_messages(cls, session_id: str) -> List[Dict[str, Any]]:
        """Retrieve all messages for a session in chronological order."""
        cls.init_db()
        with cls._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT role, content, thinking, citations_json, timestamp
                FROM mentor_messages
                WHERE session_id = ?
                ORDER BY id ASC;
            """, (session_id,))
            rows = cursor.fetchall()
            messages: List[Dict[str, Any]] = []
            for r in rows:
                citations = None
                if r["citations_json"]:
                    try:
                        citations = json.loads(r["citations_json"])
                    except Exception:
                        citations = []
                messages.append({
                    "role": r["role"],
                    "content": r["content"],
                    "thinking": r["thinking"],
                    "citations": citations or [],
                    "timestamp": r["timestamp"],
                })
            return messages

    @classmethod
    def export_session_data(cls, session_id: str) -> Optional[Dict[str, Any]]:
        """Export session metadata and message history as a serializable dict."""
        cls.init_db()
        with cls._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM mentor_sessions WHERE id = ?;", (session_id,))
            sess_row = cursor.fetchone()
            if not sess_row:
                return None
            sess_dict = dict(sess_row)
            sess_dict["messages"] = cls.get_session_messages(session_id)
            return sess_dict

    # --- CANDIDATE MEMORY MANAGEMENT ---

    @classmethod
    def get_memories(cls) -> List[str]:
        """Retrieve all persisted candidate memories as a list of facts."""
        cls.init_db()
        with cls._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT fact FROM mentor_memories ORDER BY created_at ASC;")
            rows = cursor.fetchall()
            return [r["fact"] for r in rows if r["fact"]]

    @classmethod
    def add_memory(cls, fact: str, key: Optional[str] = None) -> bool:
        """Add a candidate memory fact if it doesn't already exist."""
        clean_fact = fact.strip()
        if not clean_fact:
            return False

        cls.init_db()
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        mem_key = key or f"mem_{int(time.time() * 1000)}_{abs(hash(clean_fact)) % 10000}"

        with cls._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key FROM mentor_memories WHERE fact = ?;", (clean_fact,))
            if cursor.fetchone():
                return False  # Already exists

            cursor.execute("""
                INSERT OR REPLACE INTO mentor_memories (key, fact, created_at, updated_at)
                VALUES (?, ?, ?, ?);
            """, (mem_key, clean_fact, now_iso, now_iso))
            conn.commit()
            return True

    @classmethod
    def remove_memory(cls, fact: str) -> bool:
        """Remove a specific memory fact from the database."""
        cls.init_db()
        with cls._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM mentor_memories WHERE fact = ?;", (fact.strip(),))
            conn.commit()
            return cursor.rowcount > 0

    @classmethod
    def clear_memories(cls) -> bool:
        """Clear all stored candidate memories."""
        cls.init_db()
        with cls._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM mentor_memories;")
            conn.commit()
            return True

    # --- SYSTEM STATUS ---

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """Get summary statistics about database storage."""
        cls.init_db()
        with cls._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM mentor_sessions;")
            session_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM mentor_messages;")
            message_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM mentor_memories;")
            memory_count = cursor.fetchone()[0]

            from src.config import settings
            db_user = getattr(settings, "DB_USERNAME", None)
            db_token = getattr(settings, "DB_TOKEN", None)

            return {
                "db_path": str(cls.get_db_path()),
                "sessions_count": session_count,
                "messages_count": message_count,
                "memories_count": memory_count,
                "has_credentials": bool(db_user or db_token),
                "is_connected": True,
            }


__all__ = ["MentorDatabase"]
