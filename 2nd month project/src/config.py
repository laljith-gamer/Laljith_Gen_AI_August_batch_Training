import os
import sys
import site
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Ensure user site-packages (where google-genai, pypdf, faiss are installed) is in sys.path
user_site = site.getusersitepackages()
if user_site and user_site not in sys.path:
    sys.path.insert(0, user_site)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

for candidate in [PROJECT_ROOT.parent / ".env", PROJECT_ROOT / ".env"]:
    if candidate.exists():
        load_dotenv(dotenv_path=candidate, override=True)


class Settings:

    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    GEMINI_EMBEDDING_MODEL: str = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "3072"))

    TOP_K_JOBS: int = int(os.getenv("TOP_K_JOBS", "5"))
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.20"))
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "600"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "100"))

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
        for d in [cls.DATA_DIR, cls.RESUMES_DIR, cls.CAREER_NOTES_DIR,
                  cls.VECTORSTORE_DIR, cls.JOB_INDEX_DIR, cls.MENTOR_INDEX_DIR,
                  cls.FEEDBACK_DIR, cls.PROJECT_ROOT / "data/jobs"]:
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()


def get_gemini_client(api_key: Optional[str] = None):
    effective_key = api_key or settings.GEMINI_API_KEY
    if not effective_key:
        raise ValueError(
            "GEMINI_API_KEY is not set. Provide it in .env or enter it in the application sidebar."
        )
    from google import genai
    return genai.Client(api_key=effective_key)
