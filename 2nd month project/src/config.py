import os
import sys
import site
from pathlib import Path
from typing import Optional, Any
from dotenv import load_dotenv

# Ensure user site-packages (where google-genai, pypdf, faiss are installed) is in sys.path
user_site = site.getusersitepackages()
if user_site and user_site not in sys.path:
    sys.path.insert(0, user_site)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

for candidate in [PROJECT_ROOT.parent / ".env", PROJECT_ROOT / ".env"]:
    if candidate.exists():
        load_dotenv(dotenv_path=candidate, override=True)


def get_secret(key: str, default: Optional[Any] = None) -> Optional[Any]:
    """
    Retrieve secrets and environment settings seamlessly across Streamlit Cloud
    (st.secrets) and local environment variables (.env / os.environ).
    Supports top-level keys, lowercase keys, and [database] sections.
    Safely catches StreamlitSecretNotFoundError when secrets.toml is absent.
    """
    # 1. Try Streamlit Secrets if available
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            try:
                # Direct key match (e.g. GEMINI_API_KEY, DB_USERNAME, DB_TOKEN)
                if key in st.secrets:
                    return st.secrets[key]
                if key.lower() in st.secrets:
                    return st.secrets[key.lower()]

                # Nested [database] section check
                if key.startswith("DB_") or key.startswith("db_"):
                    sub_key = key[3:].lower()
                    if "database" in st.secrets and isinstance(st.secrets["database"], dict):
                        if sub_key in st.secrets["database"]:
                            return st.secrets["database"][sub_key]
                    if "db" in st.secrets and isinstance(st.secrets["db"], dict):
                        if sub_key in st.secrets["db"]:
                            return st.secrets["db"][sub_key]
            except Exception:
                pass
    except Exception:
        pass

    # 2. Fall back to os.environ
    return os.getenv(key, default)


class Settings:

    @classmethod
    def get_gemini_api_key(cls) -> Optional[str]:
        """Fetch active Gemini API key from Streamlit secrets, session, or env."""
        val = get_secret("GEMINI_API_KEY") or get_secret("GOOGLE_API_KEY")
        if val:
            return str(val).strip()
        return None

    @property
    def GEMINI_API_KEY(self) -> Optional[str]:
        return self.get_gemini_api_key()

    @property
    def GEMINI_MODEL(self) -> str:
        return str(get_secret("GEMINI_MODEL", "gemini-3.5-flash-lite"))

    @property
    def GEMINI_EMBEDDING_MODEL(self) -> str:
        return str(get_secret("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"))

    @property
    def EMBEDDING_DIMENSION(self) -> int:
        return int(get_secret("EMBEDDING_DIMENSION", "3072"))

    @property
    def TOP_K_JOBS(self) -> int:
        return int(get_secret("TOP_K_JOBS", "5"))

    @property
    def SIMILARITY_THRESHOLD(self) -> float:
        return float(get_secret("SIMILARITY_THRESHOLD", "0.20"))

    @property
    def CHUNK_SIZE(self) -> int:
        return int(get_secret("CHUNK_SIZE", "600"))

    @property
    def CHUNK_OVERLAP(self) -> int:
        return int(get_secret("CHUNK_OVERLAP", "100"))

    # Database Configuration for Chat History & Memory
    @property
    def DB_PATH(self) -> Path:
        raw = get_secret("DB_PATH", "data/mentor_history.db")
        return self.PROJECT_ROOT / Path(str(raw))

    @property
    def DB_USERNAME(self) -> Optional[str]:
        return get_secret("DB_USERNAME")

    @property
    def DB_TOKEN(self) -> Optional[str]:
        return get_secret("DB_TOKEN")

    PROJECT_ROOT: Path = PROJECT_ROOT
    DATA_DIR: Path = PROJECT_ROOT / "data"
    JOBS_DATA_PATH: Path = PROJECT_ROOT / Path(os.getenv("JOBS_DATA_PATH", "data/jobs/jobs.csv"))
    RESUMES_DIR: Path = PROJECT_ROOT / "data/resumes"
    CAREER_NOTES_DIR: Path = PROJECT_ROOT / Path(os.getenv("CAREER_NOTES_DIR", "data/career_notes"))
    VECTORSTORE_DIR: Path = PROJECT_ROOT / "vectorstore"
    JOB_INDEX_DIR: Path = PROJECT_ROOT / Path(os.getenv("JOB_INDEX_DIR", "vectorstore/jobs"))
    MENTOR_INDEX_DIR: Path = PROJECT_ROOT / Path(os.getenv("MENTOR_INDEX_DIR", "vectorstore/mentor"))
    FEEDBACK_DIR: Path = PROJECT_ROOT / Path(os.getenv("FEEDBACK_DIR", "data/feedback"))

    @classmethod
    def ensure_directories(cls):
        for d in [cls.DATA_DIR, cls.RESUMES_DIR, cls.CAREER_NOTES_DIR,
                  cls.VECTORSTORE_DIR, cls.JOB_INDEX_DIR, cls.MENTOR_INDEX_DIR,
                  cls.FEEDBACK_DIR, cls.PROJECT_ROOT / "data/jobs"]:
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()


def get_gemini_client(api_key: Optional[str] = None):
    effective_key = api_key or settings.get_gemini_api_key()
    if not effective_key:
        raise ValueError(
            "GEMINI_API_KEY is not set. Provide it in Streamlit Cloud Secrets, .env, or enter it in the application sidebar."
        )
    from google import genai
    return genai.Client(api_key=effective_key)
