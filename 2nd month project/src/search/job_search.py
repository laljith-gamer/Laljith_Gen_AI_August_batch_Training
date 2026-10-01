import re
import logging
from typing import List, Optional, Union
from src.config import settings
from src.models.schemas import ResumeProfile, HumanApprovedProfile, JobPosting, JobMatchResult
from src.human_loop.review import ProfileReviewManager
from src.search.embed import EmbeddingManager
from src.search.faiss_store import FaissVectorStore

logger = logging.getLogger(__name__)


class JobSearchEngine:

    def __init__(
        self,
        embed_manager: Optional[EmbeddingManager] = None,
        vector_store: Optional[FaissVectorStore] = None,
        api_key: Optional[str] = None,
    ):
        self.api_key = api_key or settings.get_gemini_api_key()
        self.embed_manager = embed_manager or EmbeddingManager(api_key=self.api_key)
        self.vector_store = vector_store or FaissVectorStore(settings.JOB_INDEX_DIR)
        if not self.vector_store.exists():
            try:
                from scripts.build_job_index import build_job_index
                logger.info("Job FAISS index missing. Auto-building...")
                build_job_index(force=False)
                self.vector_store.load()
            except Exception as e:
                logger.warning(f"Could not automatically build job index: {e}")

    @property
    def index(self):
        return self.vector_store.index if self.vector_store else None

    @staticmethod
    def build_profile_search_text(profile: ResumeProfile) -> str:
        parts = []
        if profile.target_role:
            parts.append(f"Target Role: {profile.target_role}")
        if profile.skills:
            parts.append(f"Skills: {', '.join(profile.skills)}")
        if profile.summary:
            parts.append(f"Summary: {profile.summary}")

        for exp in profile.experience:
            exp_str = f"Experience at {exp.company or 'Company'} as {exp.role or 'Role'}: {exp.description or ''}"
            if exp.technologies:
                exp_str += f" (Technologies: {', '.join(exp.technologies)})"
            parts.append(exp_str)

        for proj in profile.projects:
            proj_str = f"Project {proj.name}: {proj.description or ''}"
            if proj.technologies:
                proj_str += f" (Tech: {', '.join(proj.technologies)})"
            parts.append(proj_str)

        for edu in profile.education:
            parts.append(f"Education: {edu.degree or ''} in {edu.field or ''} from {edu.institution or ''}")

        return "\n".join(parts)

    @staticmethod
    def calculate_skill_overlap(
        candidate_skills: List[str],
        job_skills: List[str],
        job_text: str = "",
    ):
        cand_map = {re.sub(r"[^\w]", "", s.lower()): s for s in candidate_skills if s}
        job_map = {re.sub(r"[^\w]", "", s.lower()): s for s in job_skills if s}

        matched = []
        missing = []

        for clean_job_skill, orig_job_skill in job_map.items():
            if clean_job_skill in cand_map:
                matched.append(orig_job_skill)
            else:
                matched_sub = False
                for clean_cand_skill in cand_map.keys():
                    if clean_cand_skill in clean_job_skill or clean_job_skill in clean_cand_skill:
                        matched.append(orig_job_skill)
                        matched_sub = True
                        break
                if not matched_sub:
                    missing.append(orig_job_skill)

        # In real-world job postings, candidate skills also appear in title & description
        if job_text:
            text_lower = job_text.lower()
            for clean_cand_skill, orig_cand_skill in cand_map.items():
                if len(clean_cand_skill) >= 2 and re.search(r'\b' + re.escape(orig_cand_skill.lower()) + r'\b', text_lower):
                    if orig_cand_skill not in matched:
                        matched.append(orig_cand_skill)

        return matched, missing

    def search_matching_jobs(
        self,
        candidate_profile: Union[ResumeProfile, HumanApprovedProfile],
        top_k: Optional[int] = None,
        min_similarity: Optional[float] = None,
        location_filter: Optional[str] = None,
    ) -> List[JobMatchResult]:
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
                    "Human review and explicit approval are required before proceeding to job matching."
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
        elif candidate_profile is None:
            raise ValueError("No candidate profile provided to search_matching_jobs.")
        elif hasattr(candidate_profile, "skills"):
            approved = candidate_profile
        else:
            raise TypeError("Invalid profile type provided to search_matching_jobs.")

        if approved is None:
            raise ValueError("No valid candidate profile available for job matching.")

        k = top_k or settings.TOP_K_JOBS
        threshold = min_similarity if min_similarity is not None else settings.SIMILARITY_THRESHOLD

        search_text = self.build_profile_search_text(approved)
        query_vector = self.embed_manager.embed_text(search_text)

        raw_results = self.vector_store.search(query_vector, top_k=k * 2)

        job_matches: List[JobMatchResult] = []
        for meta, score in raw_results:
            if score < threshold:
                continue

            job_skills = meta.get("skills", [])
            if isinstance(job_skills, str):
                job_skills = [s.strip() for s in job_skills.split(",") if s.strip()]

            job = JobPosting(
                job_id=str(meta.get("job_id", "")),
                title=str(meta.get("title", "")),
                company=str(meta.get("company", "")),
                location=str(meta.get("location", "")),
                skills=job_skills,
                description=str(meta.get("description", "")),
                source=str(meta.get("source", "dataset")),
            )

            if location_filter and location_filter.strip():
                if location_filter.lower() not in job.location.lower():
                    continue

            matched_skills, missing_skills = self.calculate_skill_overlap(
                approved.skills, job.skills, job_text=f"{job.title} {job.description}"
            )

            explanation = (
                f"Strong semantic alignment with {job.title} at {job.company}. "
                f"Shares {len(matched_skills)} key skills ({', '.join(matched_skills[:3]) if matched_skills else 'conceptual domain alignment'})."
            )

            job_matches.append(
                JobMatchResult(
                    job=job,
                    similarity_score=round(score, 3),
                    matched_skills=matched_skills,
                    missing_skills=missing_skills,
                    match_explanation=explanation,
                )
            )

            if len(job_matches) >= k:
                break

        return job_matches
