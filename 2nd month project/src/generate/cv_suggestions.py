import json
import logging
from typing import Optional, Union
from google.genai import types

from src.config import settings, get_gemini_client
from src.models.schemas import (
    ResumeProfile,
    HumanApprovedProfile,
    JobPosting,
    CVSuggestionResult,
)
from src.human_loop.review import ProfileReviewManager
from src.generate.prompts import CV_ANALYSIS_SYSTEM_PROMPT, CV_SUGGESTION_USER_PROMPT

logger = logging.getLogger(__name__)


class CVSuggestionEngine:

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY

    def generate_suggestions(
        self,
        candidate_profile: Union[ResumeProfile, HumanApprovedProfile],
        target_job: JobPosting,
        model_name: Optional[str] = None,
    ) -> CVSuggestionResult:
        approved: Optional[ResumeProfile] = None

        is_container = (
            isinstance(candidate_profile, HumanApprovedProfile)
            or type(candidate_profile).__name__ == "HumanApprovedProfile"
            or (hasattr(candidate_profile, "is_approved") and (hasattr(candidate_profile, "approved_profile") or hasattr(candidate_profile, "original_ai_profile")))
        )

        if is_container:
            if not getattr(candidate_profile, "is_approved", False):
                status_str = getattr(candidate_profile, "status", "REQUIRES_REVIEW")
                raise PermissionError(
                    f"Candidate profile status is '{status_str}'. "
                    "Human review and explicit approval are required before proceeding to CV suggestions."
                )
            raw_approved = getattr(candidate_profile, "approved_profile", None) or getattr(candidate_profile, "original_ai_profile", None)
            if isinstance(raw_approved, dict):
                approved = ResumeProfile(**raw_approved)
            elif isinstance(raw_approved, ResumeProfile) or (hasattr(raw_approved, "skills") and hasattr(raw_approved, "target_role")):
                approved = raw_approved
        elif (
            isinstance(candidate_profile, ResumeProfile)
            or type(candidate_profile).__name__ == "ResumeProfile"
            or (hasattr(candidate_profile, "skills") and hasattr(candidate_profile, "target_role"))
        ):
            approved = candidate_profile
        elif isinstance(candidate_profile, dict):
            if candidate_profile.get("is_approved") is False:
                raise PermissionError("Candidate profile requires human review and explicit approval.")
            raw_prof = candidate_profile.get("approved_profile") or candidate_profile.get("original_ai_profile") or candidate_profile
            if isinstance(raw_prof, dict) and ("skills" in raw_prof or "target_role" in raw_prof):
                approved = ResumeProfile(**raw_prof)
            elif isinstance(raw_prof, ResumeProfile) or (hasattr(raw_prof, "skills") and hasattr(raw_prof, "target_role")):
                approved = raw_prof
        elif hasattr(candidate_profile, "skills"):
            approved = candidate_profile
        else:
            raise TypeError("Invalid profile type provided to generate_suggestions.")

        if approved is None:
            raise ValueError("No valid candidate profile available for CV suggestions.")

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required for CV suggestion generation.")

        exp_lines = []
        for exp in approved.experience:
            line = f"- {exp.role} at {exp.company}: {exp.description or ''}"
            if exp.technologies:
                line += f" [Tech: {', '.join(exp.technologies)}]"
            exp_lines.append(line)
        exp_text = "\n".join(exp_lines) if exp_lines else "No formal experience listed."

        proj_lines = []
        for proj in approved.projects:
            line = f"- {proj.name}: {proj.description or ''}"
            if proj.technologies:
                line += f" [Tech: {', '.join(proj.technologies)}]"
            proj_lines.append(line)
        proj_text = "\n".join(proj_lines) if proj_lines else "No specific projects listed."

        user_prompt = CV_SUGGESTION_USER_PROMPT.format(
            job_title=target_job.title,
            job_company=target_job.company,
            job_skills=", ".join(target_job.skills),
            job_description=target_job.description,
            candidate_target_role=approved.target_role or "Software Professional",
            candidate_skills=", ".join(approved.skills),
            candidate_summary=approved.summary or "Not provided.",
            candidate_experience=exp_text,
            candidate_projects=proj_text,
        )

        client = get_gemini_client(api_key=self.api_key)
        target_model = model_name or settings.GEMINI_MODEL

        config = types.GenerateContentConfig(
            system_instruction=CV_ANALYSIS_SYSTEM_PROMPT,
            temperature=0.2,
            response_mime_type="application/json",
            response_json_schema=CVSuggestionResult.model_json_schema(),
        )

        response = client.models.generate_content(
            model=target_model,
            contents=user_prompt,
            config=config,
        )

        raw_text = response.text or "{}"
        cleaned = raw_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        result = CVSuggestionResult.model_validate_json(cleaned)
        result.target_job_id = target_job.job_id
        result.target_job_title = target_job.title
        result.target_company = target_job.company
        return result
