"""
Autonomous Candidate Memory Extractor for SmartHire AI Career Mentor.
Analyzes user-AI chat interactions to autonomously detect and persist candidate facts,
preferences, career goals, skills, and background details into long-term browser memory.
"""

import re
import logging
from typing import List, Optional
from google.genai import types

from src.config import settings, get_gemini_client

logger = logging.getLogger(__name__)


class MentorMemoryExtractor:
    """Extracts candidate facts autonomously from conversation turns."""

    EXTRACTION_PROMPT = """Analyze this chat interaction between a candidate and an AI Career Mentor:

User text: {user_text}
AI response excerpt: {assistant_excerpt}

Existing Candidate Memories:
{existing_memories_str}

Task: Extract any NEW memorable candidate facts, goals, preferences, skills, target roles, salary preferences, or background details mentioned or implied by the user that are NOT already in Existing Candidate Memories.

Examples of candidate memory facts:
• Target career role: Senior Machine Learning Engineer.
• Salary expectation: $210k+ annual.
• Work preference: Remote only.
• Core tech stack: Python, PyTorch, Ray, AWS.

Rules:
1. Output ONLY new factual bullet points starting with '• '.
2. If NO new candidate memory facts are present, output 'NONE'.
3. Do NOT extract standard career advice given by the AI. Only extract candidate facts.
4. Keep each fact under 120 characters and very clear.
"""

    @classmethod
    def _extract_pattern_facts(cls, user_text: str, existing_memories: List[str]) -> List[str]:
        """Extract candidate details using regex pattern matching (instant, resilient to 429 rate limits)."""
        facts: List[str] = []
        low = user_text.lower()
        existing_str = " ".join(existing_memories).lower()

        # 1. Target role pattern
        role_match = re.search(
            r"(?:targeting|aiming for|looking for|applying for|want to be a|pursuing a|target role is)\s+([a-zA-Z0-9\s\-/]+?)(?:\.|\,|$|with|at|paying)",
            user_text,
            re.IGNORECASE,
        )
        if role_match:
            role = role_match.group(1).strip()
            if len(role) > 3 and role.lower() not in existing_str:
                facts.append(f"Target role: {role.title()}")

        # 2. Salary target pattern
        sal_match = re.search(
            r"(\$\d+k?\+?|\d+k\s*\+|\d+,\d+|\$\d+,\d+|\d+\s*k(?:USD)?)",
            user_text,
            re.IGNORECASE,
        )
        if sal_match:
            sal = sal_match.group(1).strip()
            if sal.lower() not in existing_str and ("salary" in low or "paying" in low or "target" in low or "compensation" in low or "$" in sal):
                facts.append(f"Salary target: {sal}")

        # 3. Work mode preference
        if "remote" in low and "remote" not in existing_str:
            facts.append("Work preference: Remote positions")
        elif "hybrid" in low and "hybrid" not in existing_str:
            facts.append("Work preference: Hybrid positions")

        # 4. Years of experience pattern
        exp_match = re.search(r"(\d+\+?\s*(?:years|yrs)\s*(?:of)?\s*(?:experience|exp)?)", user_text, re.IGNORECASE)
        if exp_match and "experience" in low:
            exp = exp_match.group(1).strip()
            if exp.lower() not in existing_str:
                facts.append(f"Experience: {exp}")

        return facts

    @classmethod
    def extract_new_facts(
        cls,
        user_text: str,
        assistant_text: str,
        existing_memories: List[str],
        api_key: Optional[str] = None,
    ) -> List[str]:
        """
        Autonomously extract new candidate facts from a chat turn.
        Combines pattern extraction (instant) with Gemini model fallback chain.
        """
        if not user_text or len(user_text.strip()) < 8:
            return []

        # Skip extraction for pure greetings / casual messages
        _lower = user_text.strip().lower().rstrip("!?.,")
        _casual = {"hi", "hello", "hey", "thanks", "thank you", "ok", "okay", "sure", "yes", "no", "bye"}
        if _lower in _casual:
            return []

        # 1. First run instant pattern extraction (0 LLM tokens)
        pattern_facts = cls._extract_pattern_facts(user_text, existing_memories)

        # Token Optimization: If pattern matching already captured facts or input is simple,
        # skip expensive LLM calls completely!
        if pattern_facts or len(user_text.split()) < 10:
            return pattern_facts

        # 2. Run Gemini extraction with fallback models for complex implicit facts
        llm_facts: List[str] = []
        key = api_key or settings.GEMINI_API_KEY

        if key:
            mem_str = "\n".join([f"• {m}" for m in existing_memories[:4]]) if existing_memories else "None."
            ast_excerpt = assistant_text[:180] if assistant_text else ""

            prompt = cls.EXTRACTION_PROMPT.format(
                user_text=user_text[:250],
                assistant_excerpt=ast_excerpt,
                existing_memories_str=mem_str,
            )

            candidate_models = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-flash-latest", "gemini-3.6-flash"]
            client = get_gemini_client(api_key=key)
            config = types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=96,
            )

            for model_name in candidate_models:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=config,
                    )
                    raw_output = (response.text or "").strip()
                    if raw_output and "NONE" not in raw_output.upper():
                        for line in raw_output.split("\n"):
                            clean_line = line.strip()
                            if clean_line.startswith("•") or clean_line.startswith("-") or clean_line.startswith("*"):
                                fact = clean_line.lstrip("•-* ").strip()
                                if fact and len(fact) > 5:
                                    llm_facts.append(fact)
                    break  # Success, exit model loop
                except Exception as exc:
                    logger.debug(f"Extraction model {model_name} failed: {exc}")
                    continue

        # Combine pattern and LLM facts, deduplicating against existing memories
        combined: List[str] = []
        existing_set = set(m.lower().strip() for m in existing_memories)

        for fact in pattern_facts + llm_facts:
            clean = fact.strip()
            if clean and clean.lower() not in existing_set:
                combined.append(clean)
                existing_set.add(clean.lower())

        return combined
