"""
Safety Guardrails and Prompt Injection Protection for SmartHire GenAI.
Enforces domain scope, rejects jailbreaks, credential exfiltration, and fraudulent requests.
"""

import re
from typing import Tuple

class SafetyGuardrails:
    """Classifies user queries to enforce career domain boundaries and prevent malicious attacks."""

    # Prompt injection and exfiltration patterns
    INJECTION_PATTERNS = [
        r"(?i)\bignore\s+(all\s+)?(previous|prior)\s+(instructions|prompts|rules)\b",
        r"(?i)\bdisregard\s+(all\s+)?(previous|prior)\s+(instructions|prompts|rules)\b",
        r"(?i)\b(show|reveal|print|expose|output|dump)\s+(me\s+)?(your\s+)?(system\s+prompt|hidden\s+prompt|instructions)\b",
        r"(?i)\b(show|reveal|print|give|extract|output)\s+(me\s+)?(your\s+)?([a-z0-9_]*api[_\s-]?keys?|secrets?|tokens?|passwords?|credentials?|envs?|environment\s+variables?)\b",
        r"(?i)\b[a-z0-9_]*api[_\s-]?keys?\b",
        r"(?i)\benvironment\s+variables?\b",
        r"(?i)\b(dan\s+mode|jailbreak|developer\s+mode)\b",
        r"(?i)\byou\s+are\s+now\s+in\s+developer\s+mode\b",
        r"(?i)\bpretend\s+you\s+have\s+no\s+(rules|guidelines|restrictions)\b",
    ]

    # Fraudulent resume faking patterns
    FRAUD_PATTERNS = [
        r"(?i)\b(fake|falsify|forge|fabricate|invent)\s+(a\s+|an\s+|my\s+|the\s+)?(resume|cv|experience|degree|diploma|certificate|credentials|qualification)\b",
        r"(?i)\bmake\s+up\s+(fake\s+)?(companies|experience|work\s+history|references)\b",
        r"(?i)\bhelp\s+me\s+lie\s+(on\s+my\s+resume|in\s+an\s+interview)\b",
    ]

    # Malicious / Exploit patterns
    MALICIOUS_PATTERNS = [
        r"(?i)\b(hack|exploit|bypass|ddos|sql\s+injection|xss|trojan|ransomware|keylogger)\b",
        r"(?i)\b(how\s+to\s+make\s+a\s+bomb|weapons|drugs)\b",
    ]

    # Broad career & professional domains allowed
    CAREER_KEYWORDS = [
        "resume", "cv", "job", "career", "interview", "skills", "salary", "hiring",
        "portfolio", "experience", "education", "roadmap", "transition", "learning",
        "certificat", "project", "role", "analyst", "engineer", "developer", "architect",
        "python", "sql", "cloud", "aws", "azure", "docker", "devops", "machine learning",
        "ai", "data", "backend", "frontend", "cybersecurity", "star method", "bullet",
        "work", "company", "position", "recruiter", "ats", "promotion", "github", "linkedin",
        "how", "what", "which", "guide", "roadmap", "advice", "suggestion", "improve"
    ]

    @classmethod
    def evaluate_input(cls, user_text: str) -> Tuple[bool, str]:
        """
        Evaluate input text.
        Returns:
            (is_allowed: bool, message: str)
        """
        if not user_text or not user_text.strip():
            return False, "Query cannot be empty."

        text = user_text.strip()

        # 1. Check for prompt injection or system extraction
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, text):
                return False, (
                    "Security Alert: Request blocked. System instructions, prompts, and credentials "
                    "cannot be exposed or overridden."
                )

        # 2. Check for fraud or resume falsification
        for pattern in cls.FRAUD_PATTERNS:
            if re.search(pattern, text):
                return False, (
                    "Ethical Guideline: SmartHire cannot assist in falsifying resumes, fabricating experience, "
                    "or forging credentials. We can assist in highlighting your genuine skills and identifying learning pathways."
                )

        # 3. Check for malware or exploits
        for pattern in cls.MALICIOUS_PATTERNS:
            if re.search(pattern, text):
                return False, (
                    "Security Alert: Request blocked. Queries related to security exploits, cyberattacks, "
                    "or malicious activities are strictly prohibited."
                )

        # 4. Scope verification: Allow if any career keyword is present or if question structure is standard career inquiry
        lower_text = text.lower()
        has_career_intent = any(kw in lower_text for kw in cls.CAREER_KEYWORDS)
        
        # Check for obvious out-of-scope queries (e.g. recipes, pop culture, weather, sports trivia)
        out_of_scope_patterns = [
            r"(?i)\b(recipe|bake|cook|weather|forecast|horoscope|soccer\s+score|nba|world\s+cup|movie\s+plot|song\s+lyrics|joke|poem)\b",
            r"(?i)\b(who\s+won\s+the|what\s+is\s+the\s+capital\s+of|write\s+a\s+story\s+about\s+dragons)\b",
        ]
        for pattern in out_of_scope_patterns:
            if re.search(pattern, text) and not has_career_intent:
                return False, (
                    "I can help with resumes, job matching, career planning, skills, and interview preparation. "
                    "This request is outside the scope of SmartHire."
                )

        return True, "Request allowed."
