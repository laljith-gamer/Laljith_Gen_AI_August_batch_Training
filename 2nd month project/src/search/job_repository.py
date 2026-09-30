"""
Centralized Job Data Repository.
Single source of truth for loading the active job corpus.
Used by Job Search, Resume Studio, and Evaluation.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

import pandas as pd

from src.config import settings
from src.models.schemas import JobPosting

logger = logging.getLogger(__name__)


class JobRepository:
    """Centralized access to the active job corpus with dataset mode awareness."""

    _cache: Optional[pd.DataFrame] = None
    _cache_path: Optional[Path] = None

    @classmethod
    def _invalidate_cache(cls):
        cls._cache = None
        cls._cache_path = None

    @classmethod
    def get_active_dataset_path(cls) -> Path:
        """Return the path to the currently active job dataset based on JOB_DATA_MODE."""
        return settings.JOBS_DATA_PATH

    @classmethod
    def get_dataset_mode(cls) -> str:
        """Return the current dataset mode."""
        return settings.JOB_DATA_MODE

    @classmethod
    def is_dataset_available(cls) -> bool:
        """Check if the active dataset file exists."""
        return cls.get_active_dataset_path().exists()

    @classmethod
    def load_jobs_dataframe(cls, force_reload: bool = False) -> pd.DataFrame:
        """Load the active job dataset as a DataFrame with caching."""
        path = cls.get_active_dataset_path()

        if not force_reload and cls._cache is not None and cls._cache_path == path:
            return cls._cache

        if not path.exists():
            mode = cls.get_dataset_mode()
            if mode == "raw_kaggle":
                raise FileNotFoundError(
                    f"Normalized Kaggle Naukri job corpus not found at {path}.\n"
                    f"Run: python scripts/download_kaggle_datasets.py --dataset naukri && python scripts/prepare_kaggle_jobs.py"
                )
            elif mode == "curated_demo":
                raise FileNotFoundError(
                    f"Curated demo job corpus not found at {path}.\n"
                    f"Ensure data/jobs/jobs_demo.csv exists."
                )
            raise FileNotFoundError(f"Job dataset not found at {path} for mode: {mode}")

        df = pd.read_csv(path)
        cls._cache = df
        cls._cache_path = path
        logger.info(f"Loaded {len(df)} jobs from {path} (mode: {cls.get_dataset_mode()})")
        return df

    @classmethod
    def load_active_jobs(cls) -> List[JobPosting]:
        """Load all jobs from the active dataset as JobPosting objects."""
        df = cls.load_jobs_dataframe()
        jobs = []
        for _, row in df.iterrows():
            skills_raw = str(row.get("skills", ""))
            skills_list = [s.strip() for s in skills_raw.split(",") if s.strip()]
            jobs.append(JobPosting(
                job_id=str(row.get("job_id", "")),
                title=str(row.get("title", "")),
                company=str(row.get("company", "")),
                location=str(row.get("location", "")),
                skills=skills_list,
                description=str(row.get("description", "")),
                source=str(row.get("source", "unknown")),
                source_dataset=str(row.get("source_dataset", "")),
            ))
        return jobs

    @classmethod
    def search_jobs_by_query(cls, query: str, limit: int = 50) -> List[JobPosting]:
        """Search jobs in the active dataset matching query terms in title, skills, or company."""
        df = cls.load_jobs_dataframe()
        if not query or not query.strip():
            return cls.get_popular_target_jobs(limit=limit)

        q = query.strip().lower()
        mask = (
            df["title"].astype(str).str.lower().str.contains(q, regex=False, na=False)
            | df["skills"].astype(str).str.lower().str.contains(q, regex=False, na=False)
            | df["company"].astype(str).str.lower().str.contains(q, regex=False, na=False)
        )
        matched_df = df[mask].head(limit)
        if matched_df.empty:
            mask_desc = df["description"].astype(str).str.lower().str.contains(q, regex=False, na=False)
            matched_df = df[mask_desc].head(limit)

        jobs = []
        for _, row in matched_df.iterrows():
            skills_raw = str(row.get("skills", ""))
            skills_list = [s.strip() for s in skills_raw.split(",") if s.strip()]
            jobs.append(JobPosting(
                job_id=str(row.get("job_id", "")),
                title=str(row.get("title", "")),
                company=str(row.get("company", "")),
                location=str(row.get("location", "")),
                skills=skills_list,
                description=str(row.get("description", "")),
                source=str(row.get("source", "unknown")),
                source_dataset=str(row.get("source_dataset", "")),
            ))
        return jobs

    @classmethod
    def get_popular_target_jobs(cls, limit: int = 50) -> List[JobPosting]:
        """Return the first `limit` representative jobs from the active dataset."""
        df = cls.load_jobs_dataframe()
        jobs = []
        for _, row in df.head(limit).iterrows():
            skills_raw = str(row.get("skills", ""))
            skills_list = [s.strip() for s in skills_raw.split(",") if s.strip()]
            jobs.append(JobPosting(
                job_id=str(row.get("job_id", "")),
                title=str(row.get("title", "")),
                company=str(row.get("company", "")),
                location=str(row.get("location", "")),
                skills=skills_list,
                description=str(row.get("description", "")),
                source=str(row.get("source", "unknown")),
                source_dataset=str(row.get("source_dataset", "")),
            ))
        return jobs

    @classmethod
    def get_job_by_id(cls, job_id: str) -> Optional[JobPosting]:
        """Look up a single job by its ID."""
        df = cls.load_jobs_dataframe()
        match = df[df["job_id"].astype(str) == str(job_id)]
        if match.empty:
            return None
        row = match.iloc[0]
        skills_raw = str(row.get("skills", ""))
        skills_list = [s.strip() for s in skills_raw.split(",") if s.strip()]
        return JobPosting(
            job_id=str(row.get("job_id", "")),
            title=str(row.get("title", "")),
            company=str(row.get("company", "")),
            location=str(row.get("location", "")),
            skills=skills_list,
            description=str(row.get("description", "")),
            source=str(row.get("source", "unknown")),
            source_dataset=str(row.get("source_dataset", "")),
        )

    @classmethod
    def get_job_count(cls) -> int:
        """Return the number of jobs in the active dataset."""
        try:
            df = cls.load_jobs_dataframe()
            return len(df)
        except FileNotFoundError:
            return 0

    @classmethod
    def get_dataset_info(cls) -> Dict[str, Any]:
        """Return metadata about the active dataset."""
        mode = cls.get_dataset_mode()
        path = cls.get_active_dataset_path()
        info: Dict[str, Any] = {
            "mode": mode,
            "path": str(path),
            "exists": path.exists(),
            "job_count": 0,
            "source_label": "Unknown",
        }

        if path.exists():
            try:
                df = cls.load_jobs_dataframe()
                info["job_count"] = len(df)
                sources = df["source"].unique().tolist() if "source" in df.columns else []
                info["sources"] = sources
            except Exception as e:
                info["error"] = str(e)

        if mode == "raw_kaggle":
            info["source_label"] = "Kaggle Naukri Production Corpus (PromptCloudHQ/jobs-on-naukricom)"
        else:
            info["source_label"] = "Verified Job Corpus"

        # Load dataset_metadata.json if available
        meta_path = settings.DATASET_METADATA_PATH
        if meta_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    info["dataset_metadata"] = json.load(f)
            except Exception:
                pass

        return info

    @classmethod
    def validate_dataset_health(cls) -> Dict[str, Any]:
        """Run diagnostic checks on dataset and index availability."""
        health: Dict[str, Any] = {
            "dataset_mode": cls.get_dataset_mode(),
            "dataset_available": False,
            "index_available": False,
            "index_stale": False,
            "issues": [],
            "commands": [],
        }

        mode = cls.get_dataset_mode()
        path = cls.get_active_dataset_path()

        # Check dataset
        if path.exists():
            health["dataset_available"] = True
            try:
                df = pd.read_csv(path)
                health["dataset_row_count"] = len(df)
            except Exception as e:
                health["issues"].append(f"Dataset exists but failed to read: {e}")
        else:
            health["issues"].append(f"Production dataset not found: {path}")
            raw_path = settings.RAW_KAGGLE_JOBS_DIR / "naukri_com-job_sample.csv"
            if not raw_path.exists():
                health["issues"].append("Raw Kaggle Naukri dataset not downloaded.")
                health["commands"].append("python scripts/download_kaggle_datasets.py --dataset naukri")
            health["commands"].append("python scripts/prepare_kaggle_jobs.py")

        # Check FAISS index
        index_file = settings.JOB_INDEX_DIR / "index.faiss"
        meta_file = settings.JOB_INDEX_DIR / "metadata.pkl"
        if index_file.exists() and meta_file.exists():
            health["index_available"] = True

            # Check staleness via index_metadata.json
            idx_meta_path = settings.INDEX_METADATA_PATH
            if idx_meta_path.exists():
                try:
                    with open(idx_meta_path, "r", encoding="utf-8") as f:
                        idx_meta = json.load(f)
                    # Compare dataset hash
                    if health["dataset_available"]:
                        import hashlib
                        current_hash = hashlib.md5(
                            path.read_bytes()
                        ).hexdigest()
                        if idx_meta.get("dataset_hash") != current_hash:
                            health["index_stale"] = True
                            health["issues"].append(
                                "FAISS index was built from a different dataset version. Rebuild recommended."
                            )
                            health["commands"].append("python scripts/build_job_index.py --force")
                except Exception:
                    pass
        else:
            health["issues"].append("FAISS job index not found.")
            health["commands"].append("python scripts/build_job_index.py --force")

        return health


__all__ = ["JobRepository"]
