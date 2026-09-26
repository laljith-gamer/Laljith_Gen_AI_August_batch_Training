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
    def calculate_skill_overlap(candidate_skills: List[str], job_skills: List[str]):
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

        return matched, missing

    def search_matching_jobs(
        self,
        candidate_profile: Union[ResumeProfile, HumanApprovedProfile],
        top_k: Optional[int] = None,
        min_similarity: Optional[float] = None,
        location_filter: Optional[str] = None,
    ) -> List[JobMatchResult]:
        if isinstance(candidate_profile, HumanApprovedProfile):
            approved = ProfileReviewManager.validate_approved(candidate_profile)
        elif isinstance(candidate_profile, ResumeProfile):
            approved = candidate_profile
        else:
            raise TypeError("Invalid profile type provided to search_matching_jobs.")

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

            matched_skills, missing_skills = self.calculate_skill_overlap(approved.skills, job.skills)

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
