"""
Script to preprocess the job dataset, generate embeddings, and build the persistent FAISS index.
Usage: python scripts/build_job_index.py [--force]
"""

import sys
import argparse
import logging
from pathlib import Path
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

def build_job_index(force: bool = False):
    csv_path = settings.JOBS_DATA_PATH
    if not csv_path.exists():
        logger.error(f"Job dataset not found at {csv_path}. Please provide a jobs.csv file.")
        sys.exit(1)

    vector_store = FaissVectorStore(settings.JOB_INDEX_DIR)
    if vector_store.exists() and not force:
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
            "source": str(row.get("source", "curated")),
        })

    logger.info(f"Generating embeddings for {len(job_texts)} job postings...")
    embed_manager = EmbeddingManager()
    vectors = embed_manager.embed_texts(job_texts)

    logger.info(f"Building FAISS index with shape {vectors.shape}...")
    vector_store.build_index(vectors, metadata_list)
    logger.info("Job index successfully built and saved!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build FAISS job search index.")
    parser.add_argument("--force", action="store_true", help="Force rebuild existing index")
    args = parser.parse_args()
    build_job_index(force=args.force)
