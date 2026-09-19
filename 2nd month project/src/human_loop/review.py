"""
Human-in-the-Loop (HITL) Profile Review and State Management.
Enforces that downstream stages only operate on human-approved candidate profiles.
"""

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from src.models.enums import ReviewStatus
from src.models.schemas import ResumeProfile, HumanApprovedProfile

class ProfileReviewManager:
    """Manages the lifecycle, human edits, and approval validation of candidate profiles."""

    @staticmethod
    def initialize_review(ai_profile: ResumeProfile) -> HumanApprovedProfile:
        """Create a new review container from raw AI extraction."""
        return HumanApprovedProfile(
            original_ai_profile=ai_profile.model_copy(deep=True),
            approved_profile=ai_profile.model_copy(deep=True),
            status=ReviewStatus.REQUIRES_REVIEW,
            is_approved=False,
            change_summary=None,
        )

    @staticmethod
    def compute_diff(original: ResumeProfile, edited: ResumeProfile) -> Dict[str, Any]:
        """Compute delta between original AI extraction and human edits."""
        changes: Dict[str, Any] = {}

        # Compare basic string fields
        for field in ["name", "email", "phone", "location", "target_role", "summary"]:
            orig_val = getattr(original, field)
            edit_val = getattr(edited, field)
            if orig_val != edit_val:
                changes[field] = {"before": orig_val, "after": edit_val}

        # Compare years of experience
        if original.years_of_experience != edited.years_of_experience:
            changes["years_of_experience"] = {
                "before": original.years_of_experience,
                "after": edited.years_of_experience,
            }

        # Compare skills
        orig_skills_set = set(original.skills)
        edit_skills_set = set(edited.skills)
        added_skills = list(edit_skills_set - orig_skills_set)
        removed_skills = list(orig_skills_set - edit_skills_set)
        if added_skills or removed_skills:
            changes["skills"] = {
                "added": added_skills,
                "removed": removed_skills,
                "total_before": len(original.skills),
                "total_after": len(edited.skills),
            }

        # Compare counts of complex items
        if len(original.experience) != len(edited.experience):
            changes["experience_count"] = {
                "before": len(original.experience),
                "after": len(edited.experience),
            }
        if len(original.education) != len(edited.education):
            changes["education_count"] = {
                "before": len(original.education),
                "after": len(edited.education),
            }
        if len(original.projects) != len(edited.projects):
            changes["projects_count"] = {
                "before": len(original.projects),
                "after": len(edited.projects),
            }

        return changes

    @classmethod
    def apply_human_approval(
        cls,
        container: HumanApprovedProfile,
        edited_profile: ResumeProfile,
    ) -> HumanApprovedProfile:
        """
        Validate, update, and mark profile as APPROVED.
        """
        diff = cls.compute_diff(container.original_ai_profile, edited_profile)
        
        container.approved_profile = edited_profile.model_copy(deep=True)
        container.is_approved = True
        container.reviewed_at = datetime.utcnow().isoformat()

        if diff:
            container.status = ReviewStatus.HUMAN_EDITED
            # Format readable summary
            summary_parts = []
            if "skills" in diff:
                s_diff = diff["skills"]
                if s_diff["added"]:
                    summary_parts.append(f"Added skills: {', '.join(s_diff['added'])}")
                if s_diff["removed"]:
                    summary_parts.append(f"Removed skills: {', '.join(s_diff['removed'])}")
            if "target_role" in diff:
                summary_parts.append(
                    f"Target role updated: '{diff['target_role']['before']}' -> '{diff['target_role']['after']}'"
                )
            for k in ["name", "email", "phone", "location", "years_of_experience", "summary"]:
                if k in diff:
                    summary_parts.append(f"Modified {k}")
            container.change_summary = "; ".join(summary_parts) if summary_parts else "Human edited fields."
        else:
            container.status = ReviewStatus.APPROVED
            container.change_summary = "Approved without modifications."

        return container

    @staticmethod
    def reject_profile(container: HumanApprovedProfile, reason: str = "") -> HumanApprovedProfile:
        """Mark profile as REJECTED."""
        container.is_approved = False
        container.status = ReviewStatus.REJECTED
        container.change_summary = f"Rejected: {reason}" if reason else "Rejected by human reviewer."
        container.reviewed_at = datetime.utcnow().isoformat()
        return container

    @staticmethod
    def validate_approved(container: Optional[HumanApprovedProfile]) -> ResumeProfile:
        """
        Ensure the profile is human-approved before downstream pipeline use.
        Raises PermissionError if called on unapproved or missing profile.
        """
        if not container:
            raise PermissionError("No candidate profile available. Please upload and parse a resume first.")
        if not container.is_approved:
            raise PermissionError(
                f"Candidate profile status is '{container.status}'. "
                "Human review and explicit approval are required before proceeding to job matching."
            )
        return container.approved_profile
