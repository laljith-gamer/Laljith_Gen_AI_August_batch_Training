"""
Kaggle Naukri Dataset Normalization Pipeline.

Reads the raw Kaggle Naukri CSV (PromptCloudHQ/jobs-on-naukricom),
normalizes columns to the application schema, cleans text,
removes duplicates, and saves the application-ready job corpus.

Usage:
    python scripts/prepare_kaggle_jobs.py
    python scripts/prepare_kaggle_jobs.py --max-rows 5000
    python scripts/prepare_kaggle_jobs.py --audit-only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import numpy as np

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "kaggle" / "jobs"
OUTPUT_PATH = PROJECT_ROOT / "data" / "jobs" / "jobs_kaggle_naukri.csv"
METADATA_PATH = PROJECT_ROOT / "data" / "jobs" / "dataset_metadata.json"

# Known raw file names from PromptCloudHQ/jobs-on-naukricom
RAW_CANDIDATES = ["naukri_com-job_sample.csv"]

# Column mapping: Naukri raw → SmartHire internal schema
# The Naukri dataset columns from download_kaggle_datasets.py validation:
#   company, jobid, joblocation_address, jobtitle, skills, jobdescription
COLUMN_MAP: Dict[str, str] = {
    "jobtitle": "title",
    "company": "company",
    "joblocation_address": "location",
    "skills": "skills",
    "jobdescription": "description",
    "jobid": "source_record_id",
}

# Additional known column aliases (safety fallback)
COLUMN_ALIASES: Dict[str, list] = {
    "title": ["jobtitle", "job_title", "Job Title", "Title"],
    "company": ["company", "Company", "company_name"],
    "location": ["joblocation_address", "location", "Location", "job_location"],
    "skills": ["skills", "Skills", "key_skills", "Key Skills"],
    "description": ["jobdescription", "job_description", "Job Description", "Description"],
    "source_record_id": ["jobid", "job_id", "Uniq Id", "id"],
}

SOURCE_NAME = "kaggle_naukri"
SOURCE_DATASET = "PromptCloudHQ/jobs-on-naukricom"


def find_raw_csv() -> Path:
    """Locate the raw Naukri CSV in the expected download directory."""
    for name in RAW_CANDIDATES:
        path = RAW_DIR / name
        if path.exists():
            return path

    # Fallback: search for any CSV in the raw dir
    if RAW_DIR.exists():
        csvs = list(RAW_DIR.glob("*.csv"))
        if csvs:
            logger.warning(f"Expected file not found. Using discovered CSV: {csvs[0].name}")
            return csvs[0]

    raise FileNotFoundError(
        f"Raw Kaggle Naukri dataset not found in {RAW_DIR}.\n"
        f"Expected filename: {RAW_CANDIDATES[0]}\n"
        f"Download it first:\n"
        f"  python scripts/download_kaggle_datasets.py --dataset naukri"
    )


def detect_and_map_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Safely detect and map raw Kaggle column names to internal schema.
    Uses COLUMN_MAP first, then falls back to COLUMN_ALIASES.
    """
    existing_cols = set(df.columns)
    rename_map = {}

    # Direct mapping
    for raw_col, target_col in COLUMN_MAP.items():
        if raw_col in existing_cols:
            rename_map[raw_col] = target_col

    # Alias fallback for any unmapped target columns
    mapped_targets = set(rename_map.values())
    for target_col, aliases in COLUMN_ALIASES.items():
        if target_col in mapped_targets:
            continue
        for alias in aliases:
            if alias in existing_cols and alias not in rename_map:
                rename_map[alias] = target_col
                break

    if rename_map:
        logger.info(f"Column mapping applied: {rename_map}")
        df = df.rename(columns=rename_map)

    return df


def clean_text(text: Optional[str]) -> str:
    """Normalize whitespace, remove HTML fragments, and clean text."""
    if not isinstance(text, str) or not text.strip():
        return ""

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Decode common HTML entities
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&nbsp;", " ").replace("&quot;", '"').replace("&#39;", "'")
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Remove escaped characters artifacts
    text = text.replace("\\n", " ").replace("\\t", " ").replace("\\r", " ")

    return text


def normalize_skills(skills_str: Optional[str]) -> str:
    """Normalize skills string: trim, deduplicate, sort."""
    if not isinstance(skills_str, str) or not skills_str.strip():
        return ""
    skills = [s.strip() for s in skills_str.split(",") if s.strip()]
    # Deduplicate case-insensitively while preserving original casing
    seen = set()
    unique = []
    for s in skills:
        key = s.lower()
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return ", ".join(unique)


def compute_dedup_key(row: pd.Series) -> str:
    """Compute a deterministic deduplication key from normalized fields."""
    parts = [
        str(row.get("title", "")).lower().strip(),
        str(row.get("company", "")).lower().strip(),
        str(row.get("location", "")).lower().strip(),
        str(row.get("description", "")).lower().strip()[:500],  # First 500 chars of description
    ]
    combined = "|".join(parts)
    return hashlib.md5(combined.encode("utf-8")).hexdigest()


def run_audit(df: pd.DataFrame, label: str = "Dataset") -> Dict:
    """Print and return audit statistics for a DataFrame."""
    total = len(df)
    stats = {"total_rows": total, "columns": list(df.columns)}

    logger.info(f"\n{'='*60}")
    logger.info(f"AUDIT: {label}")
    logger.info(f"{'='*60}")
    logger.info(f"Total rows: {total}")
    logger.info(f"Columns: {list(df.columns)}")

    for col in df.columns:
        null_count = df[col].isna().sum()
        empty_count = (df[col].astype(str).str.strip() == "").sum() if df[col].dtype == object else 0
        null_pct = round(null_count / total * 100, 1) if total > 0 else 0
        empty_pct = round(empty_count / total * 100, 1) if total > 0 else 0
        stats[col] = {
            "null_count": int(null_count),
            "null_pct": null_pct,
            "empty_count": int(empty_count),
            "empty_pct": empty_pct,
        }
        logger.info(f"  {col}: null={null_count} ({null_pct}%), empty={empty_count} ({empty_pct}%)")

    # Check for duplicates based on a subset of key fields
    key_cols = [c for c in ["title", "company", "description"] if c in df.columns]
    if key_cols:
        dupes = df.duplicated(subset=key_cols, keep="first").sum()
        stats["approximate_duplicates"] = int(dupes)
        logger.info(f"  Approximate duplicates (by {key_cols}): {dupes}")

    logger.info(f"{'='*60}\n")
    return stats


def prepare_kaggle_jobs(
    max_rows: Optional[int] = None,
    audit_only: bool = False,
) -> None:
    """Main pipeline: read raw → validate → normalize → deduplicate → save."""

    # ── Step 1: Locate raw CSV ───────────────────────────────────────────
    raw_path = find_raw_csv()
    logger.info(f"Raw dataset: {raw_path}")
    logger.info(f"File size: {raw_path.stat().st_size / (1024*1024):.2f} MB")

    # ── Step 2: Read raw CSV ─────────────────────────────────────────────
    df_raw = pd.read_csv(raw_path, encoding="utf-8-sig")
    logger.info(f"Raw rows loaded: {len(df_raw)}")
    logger.info(f"Raw columns: {list(df_raw.columns)}")

    # Audit raw data
    raw_audit = run_audit(df_raw, "Raw Kaggle Naukri Dataset")

    if audit_only:
        logger.info("Audit-only mode. No output files written.")
        return

    # ── Step 3: Map columns ──────────────────────────────────────────────
    df = detect_and_map_columns(df_raw.copy())

    # Verify required columns exist after mapping
    required = ["title", "description"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"Required columns missing after column mapping: {missing}\n"
            f"Available columns: {list(df.columns)}\n"
            f"Raw columns were: {list(df_raw.columns)}"
        )

    # ── Step 4: Clean and normalize ──────────────────────────────────────
    df["title"] = df["title"].apply(clean_text)
    df["description"] = df["description"].apply(clean_text)

    if "company" in df.columns:
        df["company"] = df["company"].apply(clean_text)
    else:
        df["company"] = ""

    if "location" in df.columns:
        df["location"] = df["location"].apply(clean_text)
    else:
        df["location"] = ""

    if "skills" in df.columns:
        df["skills"] = df["skills"].apply(normalize_skills)
    else:
        df["skills"] = ""

    # ── Step 5: Filter invalid rows ──────────────────────────────────────
    pre_filter = len(df)

    # Remove rows missing BOTH title and description
    df = df[~((df["title"] == "") & (df["description"] == ""))].reset_index(drop=True)
    # Remove rows with empty description (required for meaningful semantic search)
    df = df[df["description"].str.len() > 20].reset_index(drop=True)

    filtered_count = pre_filter - len(df)
    logger.info(f"Filtered {filtered_count} invalid rows (empty title+description or very short description).")

    # ── Step 6: Deduplicate ──────────────────────────────────────────────
    pre_dedup = len(df)
    df["_dedup_key"] = df.apply(compute_dedup_key, axis=1)
    df = df.drop_duplicates(subset="_dedup_key", keep="first").reset_index(drop=True)
    df = df.drop(columns=["_dedup_key"])
    duplicate_count = pre_dedup - len(df)
    logger.info(f"Removed {duplicate_count} duplicate rows.")

    # ── Step 7: Apply row limit if requested ─────────────────────────────
    if max_rows and len(df) > max_rows:
        logger.info(f"Limiting output to {max_rows} rows (from {len(df)}).")
        df = df.head(max_rows).reset_index(drop=True)

    # ── Step 8: Assign job IDs and provenance ────────────────────────────
    if "source_record_id" not in df.columns:
        df["source_record_id"] = ""
    df["source_record_id"] = df["source_record_id"].fillna("").astype(str)

    df["job_id"] = [f"NK_{i:05d}" for i in range(len(df))]
    df["source"] = SOURCE_NAME
    df["source_dataset"] = SOURCE_DATASET

    # ── Step 9: Select and order output columns ──────────────────────────
    output_cols = [
        "job_id", "title", "company", "location", "skills",
        "description", "source", "source_dataset", "source_record_id",
    ]
    # Add any extra columns from the raw data that might be useful
    extra_cols = []
    for col in df.columns:
        if col not in output_cols and col not in ["_dedup_key"]:
            extra_cols.append(col)
    # Include useful extra columns if present
    for extra in ["experience", "salary", "education", "industry"]:
        if extra in df.columns or extra in extra_cols:
            if extra not in output_cols:
                output_cols.append(extra)

    # Only keep columns that exist
    final_cols = [c for c in output_cols if c in df.columns]
    df_out = df[final_cols]

    # ── Step 10: Save output ─────────────────────────────────────────────
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")
    logger.info(f"Saved normalized dataset: {OUTPUT_PATH} ({len(df_out)} rows)")

    # Audit normalized data
    run_audit(df_out, "Normalized Kaggle Naukri Dataset")

    # ── Step 11: Save metadata ───────────────────────────────────────────
    file_hash = hashlib.md5(OUTPUT_PATH.read_bytes()).hexdigest()
    metadata = {
        "dataset_name": "Kaggle Naukri Job Postings",
        "source": SOURCE_NAME,
        "source_dataset": SOURCE_DATASET,
        "raw_file": str(raw_path),
        "raw_row_count": len(df_raw),
        "filtered_count": filtered_count,
        "duplicate_count": duplicate_count,
        "normalized_row_count": len(df_out),
        "columns_used": final_cols,
        "output_file": str(OUTPUT_PATH),
        "output_hash": file_hash,
        "max_rows_applied": max_rows,
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "raw_audit": raw_audit,
    }

    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"Saved dataset metadata: {METADATA_PATH}")

    # ── Summary ──────────────────────────────────────────────────────────
    logger.info(f"\n{'='*60}")
    logger.info("PIPELINE SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"  Raw rows:        {len(df_raw)}")
    logger.info(f"  Filtered rows:   {filtered_count}")
    logger.info(f"  Duplicates:      {duplicate_count}")
    logger.info(f"  Final rows:      {len(df_out)}")
    logger.info(f"  Output file:     {OUTPUT_PATH}")
    logger.info(f"  Dataset hash:    {file_hash}")
    logger.info(f"{'='*60}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize raw Kaggle Naukri job dataset for SmartHire."
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Limit output to this many rows (useful for testing or deployment size constraints).",
    )
    parser.add_argument(
        "--audit-only",
        action="store_true",
        help="Only print audit statistics without writing any output files.",
    )
    args = parser.parse_args()

    try:
        prepare_kaggle_jobs(
            max_rows=args.max_rows,
            audit_only=args.audit_only,
        )
    except FileNotFoundError as e:
        logger.error(str(e))
        return 1
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
