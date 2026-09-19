"""
CV Improvement Generator targeting selected job postings.
Produces actionable critiques, missing skill gap roadmaps, and grounded bullet rewrites.
"""

import json
import logging
from typing import Optional, Union, List
from google.genai import types

from src.config import settings, get_gemini_client
from src.models.enums import ReviewStatus
from src.models.schemas import (
    ResumeProfile,
    HumanApprovedProfile,
    JobPosting,
    CVSuggestionResult,
    BulletCritique,
)
from src.human_loop.review import ProfileReviewManager
from src.generate.prompts import CV_ANALYSIS_SYSTEM_PROMPT, CV_SUGGESTION_USER_PROMPT

logger = logging.getLogger(__name__)

class CVSuggestionEngine:
    """Generates job-aligned CV improvements with anti-hallucination enforcement."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY

    def generate_suggestions(
        self,
        candidate_profile: Union[ResumeProfile, HumanApprovedProfile],
        target_job: JobPosting,
        model_name: Optional[str] = None,
    ) -> CVSuggestionResult:
        """
        Generate tailored resume improvement suggestions for a target job.
        Strictly requires human approval when passed a HumanApprovedProfile container.
        """
        if isinstance(candidate_profile, HumanApprovedProfile):
            approved = ProfileReviewManager.validate_approved(candidate_profile)
        elif isinstance(candidate_profile, ResumeProfile):
            approved = candidate_profile
        else:
            raise TypeError("Invalid profile type provided to generate_suggestions.")

        # Format experience text
        exp_lines = []
        for exp in approved.experience:
            line = f"- {exp.role} at {exp.company}: {exp.description or ''}"
            if exp.technologies:
                line += f" [Tech: {', '.join(exp.technologies)}]"
            exp_lines.append(line)
        exp_text = "\n".join(exp_lines) if exp_lines else "No formal experience listed."

        # Format projects text
        proj_lines = []
        for proj in approved.projects:
            line = f"- {proj.name}: {proj.description or ''}"
            if proj.technologies:
                line += f" [Tech: {', '.join(proj.technologies)}]"
            proj_lines.append(line)
        proj_text = "\n".join(proj_lines) if proj_lines else "No specific projects listed."

        # Format prompt
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

        if self.api_key:
            try:
                return self._call_gemini_cv_generation(user_prompt, target_job, model_name)
            except Exception as e:
                logger.warning(f"Gemini CV suggestion generation failed: {e}. Using deterministic fallback.")
                return self._generate_fallback_suggestions(approved, target_job)
        else:
            return self._generate_fallback_suggestions(approved, target_job)

    def _call_gemini_cv_generation(
        self,
        prompt: str,
        job: JobPosting,
        model_name: Optional[str] = None,
    ) -> CVSuggestionResult:
        client = get_gemini_client(api_key=self.api_key)
        target_model = model_name or settings.GEMINI_MODEL

        config = types.GenerateContentConfig(
            system_instruction=CV_ANALYSIS_SYSTEM_PROMPT,
            temperature=0.2,
            response_mime_type="application/json",
            response_json_schema=CVSuggestionResult.model_json_schema(),
        )

        try:
            response = client.models.generate_content(
                model=target_model,
                contents=prompt,
                config=config,
            )
        except Exception as exc:
            fallback = settings.GEMINI_FALLBACK_MODEL
            if fallback and fallback != target_model:
                logger.warning(f"Primary model failed ({exc}). Retrying CV generation with {fallback}...")
                response = client.models.generate_content(
                    model=fallback,
                    contents=prompt,
                    config=config,
                )
            else:
                raise exc

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
        # Ensure job metadata consistency
        result.target_job_id = job.job_id
        result.target_job_title = job.title
        result.target_company = job.company
        return result

    def _generate_fallback_suggestions(
        self,
        approved: ResumeProfile,
        job: JobPosting,
    ) -> CVSuggestionResult:
        """Deterministic fallback CV suggestions for offline/testing mode."""
        from src.search.job_search import JobSearchEngine
        matched, missing = JobSearchEngine.calculate_skill_overlap(approved.skills, job.skills)

        weak_bullets = []
        if approved.summary:
            weak_bullets.append(
                BulletCritique(
                    original_bullet=approved.summary[:80] + "...",
                    weakness_reason="Broad and generic overview without direct emphasis on target role keywords.",
                    suggested_rewrite=f"Results-oriented professional specializing in {', '.join(matched[:3]) if matched else 'core technologies'}, aligned with {job.title} expectations.",
                )
            )
        else:
            weak_bullets.append(
                BulletCritique(
                    original_bullet="No formal summary provided.",
                    weakness_reason="Missing an executive hook to anchor reader attention.",
                    suggested_rewrite=f"Dedicated professional pursuing {job.title} opportunities with strong background in {', '.join(approved.skills[:3])}.",
                )
            )

        suggestions = [
            f"Prioritize mastering {missing[0]} to directly meet the core qualification requirements." if missing else "Highlight existing competencies prominently in top section.",
            f"Tailor experience bullet points to emphasize problem-solving relevant to {job.company}.",
            "Quantify project outcomes with measurable performance, scalability, or throughput metrics.",
        ]

        rewritten_summary = (
            f"Dynamic {approved.target_role or job.title} with demonstrated expertise in {', '.join(approved.skills[:4])}. "
            f"Passionate about applying core technical skills to deliver scalable solutions at {job.company}."
        )

        rewritten_bullets = [
            f"Engineered production services utilizing {', '.join(approved.skills[:2]) if approved.skills else 'core stack'}, improving maintainability and code reliability.",
            f"Collaborated cross-functionally to design and deploy software features meeting enterprise performance benchmarks.",
        ]

        return CVSuggestionResult(
            target_job_id=job.job_id,
            target_job_title=job.title,
            target_company=job.company,
            missing_skills=missing,
            weak_bullets=weak_bullets,
            actionable_suggestions=suggestions,
            rewritten_summary=rewritten_summary,
            rewritten_bullets=rewritten_bullets,
            grounding_notes=f"Generated based on job requirements for {job.title} at {job.company}. Skills not present in resume are marked as development areas.",
            status=ReviewStatus.REQUIRES_REVIEW,
        )
