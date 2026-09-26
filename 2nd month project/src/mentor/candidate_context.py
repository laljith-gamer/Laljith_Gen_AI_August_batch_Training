"""
Candidate Resume Context Extractor and Formatter for AI Career Mentor.
Extracts structured and unstructured resume data from session state or profile models,
allowing the Career Mentor to seamlessly personalize coaching, gap analysis, and interview prep.
"""

from typing import Optional, Dict, Any, List
import logging
from src.models.schemas import ResumeProfile, HumanApprovedProfile

logger = logging.getLogger(__name__)


class CandidateContextManager:
    """Extracts, formats, and manages candidate context for the AI Career Mentor."""

    @classmethod
    def extract_from_session_state(cls, session_state: Any) -> Dict[str, Any]:
        """Extract a structured summary from Streamlit session_state."""
        container: Optional[HumanApprovedProfile] = session_state.get("human_profile_container")
        extracted_text: str = session_state.get("extracted_resume_text", "")
        uploaded_file_name: Optional[str] = session_state.get("uploaded_file_name")

        profile: Optional[ResumeProfile] = None
        if container:
            profile = container.approved_profile or container.original_ai_profile

        return cls.format_profile_summary(
            profile=profile,
            raw_text=extracted_text,
            filename=uploaded_file_name,
        )

    @classmethod
    def format_profile_summary(
        cls,
        profile: Optional[ResumeProfile] = None,
        raw_text: str = "",
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Convert a ResumeProfile into a comprehensive dictionary for prompting and UI."""
        if not profile and not (raw_text and raw_text.strip()):
            return {
                "has_resume": False,
                "name": None,
                "target_role": None,
                "years_of_experience": None,
                "skills": [],
                "skills_str": "",
                "experience_summary": [],
                "education_summary": [],
                "projects_summary": [],
                "certifications": [],
                "summary": None,
                "filename": filename,
                "formatted_prompt_block": (
                    "No candidate resume has been uploaded yet. Provide generalized career coaching "
                    "frameworks and politely invite the candidate to upload their resume for personalized advice."
                ),
            }

        name = (profile.name.strip() if profile and profile.name else "Candidate")
        target_role = (profile.target_role.strip() if profile and profile.target_role else "Technology / Career Professional")
        years_exp = (profile.years_of_experience if profile and profile.years_of_experience is not None else None)
        skills = [s.strip() for s in (profile.skills if profile and profile.skills else []) if s.strip()]
        skills_str = ", ".join(skills[:30]) if skills else "Not explicitly listed"

        # Experience items
        exp_list: List[str] = []
        if profile and profile.experience:
            for exp in profile.experience[:5]:
                role_str = exp.role or "Engineer / Specialist"
                comp_str = exp.company or "Organization"
                dates = f"({exp.start_date or ''} - {exp.end_date or 'Present'})"
                tech = f" [Tech: {', '.join(exp.technologies)}]" if exp.technologies else ""
                desc = f": {exp.description[:180]}..." if exp.description else ""
                exp_list.append(f"{role_str} at {comp_str} {dates}{tech}{desc}")

        # Education items
        edu_list: List[str] = []
        if profile and profile.education:
            for edu in profile.education[:3]:
                deg = f"{edu.degree or 'Degree'} in {edu.field or 'Field'}"
                inst = f" ({edu.institution})" if edu.institution else ""
                edu_list.append(f"{deg}{inst}")

        # Projects
        proj_list: List[str] = []
        if profile and profile.projects:
            for proj in profile.projects[:4]:
                p_tech = f" [{', '.join(proj.technologies)}]" if proj.technologies else ""
                p_desc = f": {proj.description[:140]}..." if proj.description else ""
                proj_list.append(f"{proj.name}{p_tech}{p_desc}")

        summary = (profile.summary.strip() if profile and profile.summary else "")

        # Formatted prompt dossier
        lines = [
            "=== CANDIDATE RESUME DOSSIER ===",
            f"Candidate Full Name: {name}",
            f"Target Career Orientation: {target_role}",
        ]
        if years_exp is not None:
            lines.append(f"Years of Professional Experience: {years_exp:.1f} years")
        if skills:
            lines.append(f"Verified Technical & Domain Skills ({len(skills)}): {skills_str}")
        if exp_list:
            lines.append("Professional Work Experience:")
            for item in exp_list:
                lines.append(f"  • {item}")
        if proj_list:
            lines.append("Notable Technical Projects:")
            for item in proj_list:
                lines.append(f"  • {item}")
        if edu_list:
            lines.append("Education & Academic Background:")
            for item in edu_list:
                lines.append(f"  • {item}")
        if profile and profile.certifications:
            lines.append(f"Certifications: {', '.join(profile.certifications[:5])}")
        if summary:
            lines.append(f"Executive Summary / Bio: {summary}")
        if filename:
            lines.append(f"Source Document: {filename}")
        lines.append("=== END CANDIDATE RESUME DOSSIER ===")

        prompt_block = "\n".join(lines)

        return {
            "has_resume": True,
            "name": name,
            "target_role": target_role,
            "years_of_experience": years_exp,
            "skills": skills,
            "skills_str": skills_str,
            "experience_summary": exp_list,
            "education_summary": edu_list,
            "projects_summary": proj_list,
            "certifications": profile.certifications if profile else [],
            "summary": summary,
            "filename": filename,
            "formatted_prompt_block": prompt_block,
        }

    @classmethod
    def get_initial_memories(cls, candidate_ctx: Dict[str, Any]) -> List[str]:
        """Extract high-level candidate memory facts to persist in IndexedDB and chat sessions."""
        if not candidate_ctx.get("has_resume"):
            return []
        memories: List[str] = []
        if candidate_ctx.get("name"):
            memories.append(f"Candidate's name is {candidate_ctx['name']}.")
        if candidate_ctx.get("target_role"):
            memories.append(f"Target career role: {candidate_ctx['target_role']}.")
        if candidate_ctx.get("years_of_experience") is not None:
            memories.append(f"Possesses {candidate_ctx['years_of_experience']:.1f} years of relevant experience.")
        if candidate_ctx.get("skills"):
            top_skills = ", ".join(candidate_ctx["skills"][:10])
            memories.append(f"Verified core competencies: {top_skills}.")
        if candidate_ctx.get("summary"):
            clean_summary = candidate_ctx['summary'].strip()[:140]
            memories.append(f"Professional profile summary: {clean_summary}...")
        return memories

