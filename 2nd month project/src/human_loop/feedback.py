"""
Lightweight feedback storage and analytics for Human-in-the-Loop workflows.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from src.config import settings
from src.models.enums import FeedbackRating

class FeedbackManager:
    """Handles logging and aggregation of human feedback across all subsystems."""

    @classmethod
    def _get_log_path(cls, log_name: str) -> Path:
        settings.FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
        return settings.FEEDBACK_DIR / f"{log_name}.jsonl"

    @classmethod
    def _append_record(cls, log_name: str, record: Dict[str, Any]):
        path = cls._get_log_path(log_name)
        record_with_meta = {
            "timestamp": datetime.utcnow().isoformat(),
            **record,
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record_with_meta) + "\n")

    @classmethod
    def record_job_feedback(cls, job_id: str, job_title: str, rating: str, candidate_role: str):
        """Record human relevance feedback for a retrieved job."""
        cls._append_record(
            "job_feedback",
            {
                "type": "job_matching",
                "job_id": job_id,
                "job_title": job_title,
                "rating": rating,  # 'relevant' or 'irrelevant'
                "candidate_role": candidate_role,
            },
        )

    @classmethod
    def record_mentor_feedback(
        cls,
        question: str,
        answer: str,
        rating: str,
        sources: List[str],
        comment: str = "",
    ):
        """Record human satisfaction and correctness feedback for an AI mentor response."""
        cls._append_record(
            "mentor_feedback",
            {
                "type": "mentor_answer",
                "rating": rating,  # 'helpful' or 'not_helpful'
                "question": question,
                "answer_snippet": answer[:150] + "..." if len(answer) > 150 else answer,
                "sources": sources,
                "comment": comment,
            },
        )

    @classmethod
    def record_cv_feedback(
        cls,
        target_job_id: str,
        decision: str,  # 'accepted', 'edited', 'rejected', 'regenerated'
        change_note: str = "",
    ):
        """Record user action on generated CV suggestions."""
        cls._append_record(
            "cv_feedback",
            {
                "type": "cv_improvement",
                "target_job_id": target_job_id,
                "decision": decision,
                "change_note": change_note,
            },
        )

    @classmethod
    def get_feedback_metrics(cls) -> Dict[str, Any]:
        """Aggregate feedback metrics for the evaluation dashboard."""
        metrics: Dict[str, Any] = {
            "total_job_feedback": 0,
            "job_relevant_count": 0,
            "job_irrelevant_count": 0,
            "job_relevance_rate": 0.0,
            "total_mentor_feedback": 0,
            "mentor_helpful_count": 0,
            "mentor_unhelpful_count": 0,
            "mentor_helpfulness_rate": 0.0,
            "total_cv_actions": 0,
            "cv_accepted": 0,
            "cv_edited": 0,
            "cv_rejected": 0,
        }

        # Read job feedback
        job_log = cls._get_log_path("job_feedback")
        if job_log.exists():
            with open(job_log, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        metrics["total_job_feedback"] += 1
                        if data.get("rating") == "relevant":
                            metrics["job_relevant_count"] += 1
                        else:
                            metrics["job_irrelevant_count"] += 1

            if metrics["total_job_feedback"] > 0:
                metrics["job_relevance_rate"] = round(
                    metrics["job_relevant_count"] / metrics["total_job_feedback"], 3
                )

        # Read mentor feedback
        mentor_log = cls._get_log_path("mentor_feedback")
        if mentor_log.exists():
            with open(mentor_log, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        metrics["total_mentor_feedback"] += 1
                        if data.get("rating") == "helpful":
                            metrics["mentor_helpful_count"] += 1
                        else:
                            metrics["mentor_unhelpful_count"] += 1

            if metrics["total_mentor_feedback"] > 0:
                metrics["mentor_helpfulness_rate"] = round(
                    metrics["mentor_helpful_count"] / metrics["total_mentor_feedback"], 3
                )

        # Read CV feedback
        cv_log = cls._get_log_path("cv_feedback")
        if cv_log.exists():
            with open(cv_log, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        metrics["total_cv_actions"] += 1
                        dec = data.get("decision")
                        if dec == "accepted":
                            metrics["cv_accepted"] += 1
                        elif dec == "edited":
                            metrics["cv_edited"] += 1
                        elif dec == "rejected":
                            metrics["cv_rejected"] += 1

        return metrics
