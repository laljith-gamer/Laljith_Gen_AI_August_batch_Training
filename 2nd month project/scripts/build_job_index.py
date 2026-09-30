"""
Build the FAISS job search index from the active job dataset.

Reads the active dataset (determined by JOB_DATA_MODE), generates
Gemini embeddings, and builds a persistent FAISS IndexFlatIP index
with metadata for semantic job matching.

Usage:
    python scripts/build_job_index.py
    python scripts/build_job_index.py --force
"""

import sys
import json
import hashlib
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import settings
from src.search.embed import EmbeddingManager
from src.search.faiss_store import FaissVectorStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def build_job_index(force: bool = False, limit: int | None = None):
    """Build the FAISS job index from the active job dataset."""
    mode = settings.JOB_DATA_MODE
    csv_path = settings.JOBS_DATA_PATH

    logger.info(f"Dataset mode: {mode}")
    logger.info(f"Dataset path: {csv_path}")

    if not csv_path.exists():
        if mode == "raw_kaggle":
            logger.error(
                f"Normalized Kaggle Naukri dataset not found at {csv_path}.\n"
                f"Run: python scripts/prepare_kaggle_jobs.py\n"
                f"Or set JOB_DATA_MODE=curated_demo to use the demo dataset."
            )
        else:
            logger.error(f"Job dataset not found at {csv_path}. Please provide the dataset file.")
        sys.exit(1)

    vector_store = FaissVectorStore(settings.JOB_INDEX_DIR)
    if vector_store.exists() and not force:
        # Check staleness
        idx_meta_path = settings.INDEX_METADATA_PATH
        if idx_meta_path.exists():
            try:
                with open(idx_meta_path, "r", encoding="utf-8") as f:
                    idx_meta = json.load(f)
                current_hash = hashlib.md5(csv_path.read_bytes()).hexdigest()
                if idx_meta.get("dataset_hash") != current_hash:
                    logger.warning(
                        "FAISS index was built from a different dataset version.\n"
                        "Rebuilding automatically. Use --force to skip this check."
                    )
                    force = True
                else:
                    logger.info(
                        f"FAISS index already exists at {settings.JOB_INDEX_DIR} "
                        f"and matches current dataset. Use --force to rebuild."
                    )
                    return
            except Exception:
                pass

        if not force:
            logger.info(f"FAISS index already exists at {settings.JOB_INDEX_DIR}. Use --force to rebuild.")
            return

    logger.info(f"Loading job dataset from {csv_path}...")
    df = pd.read_csv(csv_path)

    # Standardize and map columns
    required_cols = ["title", "description"]
    for c in required_cols:
        if c not in df.columns:
            logger.error(f"Missing required column '{c}' in job dataset.")
            sys.exit(1)

    df["title"] = df["title"].fillna("Untitled Role")
    df["company"] = df["company"].fillna("Confidential Company") if "company" in df.columns else "Company"
    df["location"] = df["location"].fillna("Remote / Unspecified") if "location" in df.columns else "Location"
    df["skills"] = df["skills"].fillna("") if "skills" in df.columns else ""
    df["description"] = df["description"].fillna("")
    if "job_id" in df.columns:
        df["job_id"] = df["job_id"].fillna(pd.Series(df.index.astype(str)))
    else:
        df["job_id"] = [f"JOB_{i}" for i in range(len(df))]

    # Drop empty descriptions
    initial_count = len(df)
    df = df[df["description"].str.strip() != ""].reset_index(drop=True)
    logger.info(f"Ingested {len(df)} valid jobs (filtered from {initial_count} records).")

    if limit and limit > 0:
        logger.info(f"Applying limit: indexing first {limit} jobs.")
        df = df.head(limit).reset_index(drop=True)

    # Build semantic text representation for each job posting
    job_texts = []
    metadata_list = []

    for _, row in df.iterrows():
        skills_str = str(row["skills"])
        skills_list = [s.strip() for s in skills_str.split(",") if s.strip()]

        doc_text = (
            f"Job Title: {row['title']}\n"
            f"Company: {row['company']}\n"
            f"Location: {row['location']}\n"
            f"Required Skills: {skills_str}\n"
            f"Job Description:\n{row['description']}"
        )
        job_texts.append(doc_text)

        metadata_list.append({
            "job_id": str(row["job_id"]),
            "title": str(row["title"]),
            "company": str(row["company"]),
            "location": str(row["location"]),
            "skills": skills_list,
            "description": str(row["description"]),
            "source": str(row.get("source", "kaggle_naukri")),
            "source_dataset": str(row.get("source_dataset", "PromptCloudHQ/jobs-on-naukricom")),
        })

    logger.info(f"Generating embeddings for {len(job_texts)} job postings...")
    embed_manager = EmbeddingManager()
    vectors = embed_manager.embed_texts(job_texts)

    logger.info(f"Building FAISS index with shape {vectors.shape}...")
    vector_store.build_index(vectors, metadata_list)
    logger.info("Job index successfully built and saved!")

    # Save index metadata for staleness detection
    dataset_hash = hashlib.md5(csv_path.read_bytes()).hexdigest()
    index_metadata = {
        "dataset_mode": mode,
        "dataset_path": str(csv_path),
        "dataset_hash": dataset_hash,
        "dataset_row_count": len(df),
        "indexed_job_count": len(metadata_list),
        "embedding_model": settings.GEMINI_EMBEDDING_MODEL,
        "embedding_dimension": vectors.shape[1] if len(vectors) > 0 else settings.EMBEDDING_DIMENSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    idx_meta_path = settings.INDEX_METADATA_PATH
    idx_meta_path.parent.mkdir(parents=True, exist_ok=True)
    with open(idx_meta_path, "w", encoding="utf-8") as f:
        json.dump(index_metadata, f, indent=2)
    logger.info(f"Index metadata saved to {idx_meta_path}")

    logger.info(f"\nIndex Summary:")
    logger.info(f"  Mode:        {mode}")
    logger.info(f"  Source:      {csv_path}")
    logger.info(f"  Jobs:        {len(metadata_list)}")
    logger.info(f"  Dimensions:  {vectors.shape[1] if len(vectors) > 0 else 'N/A'}")
    logger.info(f"  Hash:        {dataset_hash}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build FAISS job search index.")
    parser.add_argument("--force", action="store_true", help="Force rebuild existing index")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of jobs to embed/index")
    args = parser.parse_args()
    build_job_index(force=args.force, limit=args.limit)
