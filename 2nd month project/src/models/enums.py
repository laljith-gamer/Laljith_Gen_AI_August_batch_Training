"""
Enumerations for SmartHire GenAI
"""

from enum import Enum

class WorkflowState(str, Enum):
    """Workflow state machine progression."""
    NO_RESUME = "NO_RESUME"
    RESUME_UPLOADED = "RESUME_UPLOADED"
    PROFILE_PARSED = "PROFILE_PARSED"
    PROFILE_REVIEW = "PROFILE_REVIEW"
    PROFILE_APPROVED = "PROFILE_APPROVED"
    JOB_MATCHED = "JOB_MATCHED"
    CV_ANALYZED = "CV_ANALYZED"
    MENTOR_READY = "MENTOR_READY"

class ReviewStatus(str, Enum):
    """Human-in-the-Loop review status for parsed profile and suggestions."""
    AI_GENERATED = "AI_GENERATED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    HUMAN_EDITED = "HUMAN_EDITED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class FeedbackRating(str, Enum):
    """User feedback classification."""
    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"
    RELEVANT = "relevant"
    IRRELEVANT = "irrelevant"
