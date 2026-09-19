"""
Structured Audit Logging for SmartHire GenAI
Ensures full auditability of AI operations without exposing secrets or credentials.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from src.config import settings

class AuditLogger:
    """Logs system events, AI inferences, and human approvals for compliance and transparency."""

    @classmethod
    def _get_audit_path(cls) -> Path:
        settings.FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
        return settings.FEEDBACK_DIR / "audit.jsonl"

    @classmethod
    def log_event(
        cls,
        event_type: str,
        actor: str,  # 'AI', 'USER', 'SYSTEM'
        status: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Record an auditable event.
        Filters out any potential secrets, API keys, or raw full documents.
        """
        safe_details = {}
        if details:
            for k, v in details.items():
                lower_k = k.lower()
                # Security: never log keys or tokens
                if any(sec in lower_k for sec in ["key", "token", "secret", "password"]):
                    safe_details[k] = "[REDACTED]"
                elif isinstance(v, str) and len(v) > 500:
                    # Truncate overly long text fields
                    safe_details[k] = v[:500] + "... [TRUNCATED]"
                else:
                    safe_details[k] = v

        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "actor": actor,
            "status": status,
            "details": safe_details,
        }

        try:
            with open(cls._get_audit_path(), "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            # Audit failures must not crash the primary user journey
            pass

    @classmethod
    def get_recent_logs(cls, limit: int = 50) -> list:
        """Retrieve recent audit events for UI dashboard."""
        path = cls._get_audit_path()
        if not path.exists():
            return []
        logs = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        logs.append(json.loads(line))
                    except Exception:
                        continue
        return logs[-limit:]
