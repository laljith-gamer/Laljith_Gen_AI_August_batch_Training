"""
Resume Dataset Manager for SmartHire GenAI.
Provides cached access to Kaggle Resume.csv (2,484 resumes across 24 categories)
with text normalization, category indexing, and fast preview extraction.
"""

import os
import re
import unicodedata
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from functools import lru_cache
import pandas as pd

from src.config import settings

logger = logging.getLogger(__name__)

class ResumeDatasetManager:
    """Manages cached access and normalization for Resume.csv dataset."""

    _df_cache: Optional[pd.DataFrame] = None
    _dataset_path: Optional[Path] = None

    @classmethod
    def find_dataset_path(cls) -> Optional[Path]:
        """Locate Resume.csv across common project paths."""
        if cls._dataset_path and cls._dataset_path.exists():
            return cls._dataset_path

        candidates = [
            # Canonical downloaded Kaggle location.
            settings.PROJECT_ROOT / "data/raw/kaggle/resumes/Resume.csv",
            # Kaggle's extracted archive layout.
            settings.PROJECT_ROOT / "data/raw/kaggle/resumes/Resume/Resume.csv",
            # Existing/local compatibility locations.
            settings.PROJECT_ROOT / "Resume.csv",
            settings.PROJECT_ROOT.parent / "Resume.csv",
            settings.PROJECT_ROOT / "data/resumes/Resume.csv",
            Path(r"C:\Users\ASUS\Desktop\personal\genai-inter\2nd month project\Resume.csv"),
            Path(r"C:\Users\ASUS\Desktop\personal\genai-inter\Resume.csv"),
        ]

        for p in candidates:
            if p.exists():
                cls._dataset_path = p
                return p

        return None

    @classmethod
    def is_available(cls) -> bool:
        """Check if Resume.csv exists."""
        return cls.find_dataset_path() is not None

    @classmethod
    def load_dataset(cls, force_reload: bool = False) -> pd.DataFrame:
        """Load and cache the resume dataset."""
        if cls._df_cache is not None and not force_reload:
            return cls._df_cache

        path = cls.find_dataset_path()
        if not path:
            raise FileNotFoundError("Resume.csv not found in project or parent directory.")

        logger.info(f"Loading Resume dataset from: {path}")
        df = pd.read_csv(path, dtype={"ID": str, "Category": str})
        # Standardize ID column
        df["ID"] = df["ID"].astype(str).str.strip()
        df["Category"] = df["Category"].astype(str).str.strip()
        cls._df_cache = df
        return df

    @classmethod
    def get_categories(cls) -> List[str]:
        """Return sorted unique industry categories."""
        df = cls.load_dataset()
        categories = sorted(df["Category"].dropna().unique().tolist())
        return categories

    @classmethod
    def get_category_counts(cls) -> Dict[str, int]:
        """Return dictionary mapping category to count of resumes."""
        df = cls.load_dataset()
        return df["Category"].value_counts().to_dict()

    @classmethod
    def clean_resume_text(cls, raw_text: str) -> str:
        """
        Clean unicode replacement artifacts, excess whitespace, and formatting glitches.
        Normalizes unicode characters and replaces corrupted bullet symbols.
        """
        if not raw_text:
            return ""

        # Normalize unicode characters
        text = unicodedata.normalize("NFKD", raw_text)

        # Replace unicode replacement character or unprintable control sequences with bullet
        text = re.sub(r"[\ufffd\uff0d\x80-\x9f]+", " • ", text)

        # Normalize carriage returns
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Replace tabs and excessive consecutive horizontal spaces
        text = re.sub(r"[ \t]+", " ", text)

        # Collapse excessive newlines (keep maximum 2)
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    @classmethod
    def get_resumes_by_category(cls, category: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieve sample resumes for a specific category with clean role/summary preview.
        """
        df = cls.load_dataset()
        sub_df = df[df["Category"] == category]
        if sub_df.empty:
            # Fallback to case-insensitive match
            sub_df = df[df["Category"].str.upper() == category.upper()]

        results = []
        for _, row in sub_df.head(limit).iterrows():
            raw_text = str(row.get("Resume_str", ""))
            cleaned_snippet = cls.clean_resume_text(raw_text[:400])
            
            # Extract first non-empty line as candidate's title/headline
            lines = [line.strip() for line in cleaned_snippet.split("\n") if line.strip()]
            preview_headline = lines[0] if lines else f"Resume {row['ID']}"
            if len(preview_headline) > 60:
                preview_headline = preview_headline[:57] + "..."

            results.append({
                "id": str(row["ID"]),
                "category": str(row["Category"]),
                "headline": preview_headline,
                "snippet": cleaned_snippet[:200] + ("..." if len(cleaned_snippet) > 200 else ""),
                "char_length": len(raw_text),
            })

        return results

    @classmethod
    def get_resume(cls, resume_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single resume by its ID with both raw and cleaned text.
        """
        df = cls.load_dataset()
        target_id = str(resume_id).strip()
        matched = df[df["ID"] == target_id]
        if matched.empty:
            return None

        row = matched.iloc[0]
        raw_text = str(row.get("Resume_str", ""))
        cleaned_text = cls.clean_resume_text(raw_text)

        return {
            "id": target_id,
            "category": str(row.get("Category", "General")),
            "raw_text": raw_text,
            "cleaned_text": cleaned_text,
            "html": str(row.get("Resume_html", "")),
        }
