"""
Centralized Configuration for SmartHire GenAI
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Base paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PARENT_ROOT = PROJECT_ROOT.parent

# Explicitly target user specified .env location: C:\Users\ASUS\Desktop\personal\genai-inter\.env
PARENT_ENV = Path(r"C:\Users\ASUS\Desktop\personal\genai-inter\.env")
if PARENT_ENV.exists():
    load_dotenv(dotenv_path=PARENT_ENV, override=True)

# Also check relative parent and local project .env (local project overrides)
for candidate in [PARENT_ROOT / ".env", PROJECT_ROOT / ".env"]:
    if candidate.exists():
        load_dotenv(dotenv_path=candidate, override=True)

class Settings:
    """Application configuration settings."""

    # API Keys & LLM Configuration
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    GEMINI_FALLBACK_MODEL: str = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite")
    GEMINI_EMBEDDING_MODEL: str = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "3072"))

    # Search & Retrieval Configuration
    TOP_K_JOBS: int = int(os.getenv("TOP_K_JOBS", "5"))
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.20"))
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "600"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "100"))

    # Directory Paths
    PROJECT_ROOT: Path = PROJECT_ROOT
    DATA_DIR: Path = PROJECT_ROOT / "data"
    JOBS_DATA_PATH: Path = PROJECT_ROOT / os.getenv("JOBS_DATA_PATH", "data/jobs/jobs.csv")
    RESUMES_DIR: Path = PROJECT_ROOT / "data/resumes"
    CAREER_NOTES_DIR: Path = PROJECT_ROOT / os.getenv("CAREER_NOTES_DIR", "data/career_notes")
    VECTORSTORE_DIR: Path = PROJECT_ROOT / "vectorstore"
    JOB_INDEX_DIR: Path = PROJECT_ROOT / os.getenv("JOB_INDEX_DIR", "vectorstore/jobs")
    MENTOR_INDEX_DIR: Path = PROJECT_ROOT / os.getenv("MENTOR_INDEX_DIR", "vectorstore/mentor")
    FEEDBACK_DIR: Path = PROJECT_ROOT / os.getenv("FEEDBACK_DIR", "data/feedback")

    @classmethod
    def ensure_directories(cls):
        """Ensure that required runtime directories exist."""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.RESUMES_DIR.mkdir(parents=True, exist_ok=True)
        cls.CAREER_NOTES_DIR.mkdir(parents=True, exist_ok=True)
        cls.VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)
        cls.JOB_INDEX_DIR.mkdir(parents=True, exist_ok=True)
        cls.MENTOR_INDEX_DIR.mkdir(parents=True, exist_ok=True)
        cls.FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
        (cls.PROJECT_ROOT / "data/jobs").mkdir(parents=True, exist_ok=True)

settings = Settings()
settings.ensure_directories()

def get_gemini_client(api_key: Optional[str] = None):
    """
    Get configured Google GenAI client.
    Supports passing an explicit API key (e.g. from UI input) or falling back to environment.
    """
    effective_key = api_key or settings.GEMINI_API_KEY
    if not effective_key:
        raise ValueError(
            "GEMINI_API_KEY is not set. Please provide it in your .env file or enter it in the application sidebar."
        )
    try:
        from google import genai
        return genai.Client(api_key=effective_key)
    except Exception as e:
        raise RuntimeError(f"Failed to initialize Google GenAI Client: {e}")
