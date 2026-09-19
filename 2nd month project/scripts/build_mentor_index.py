"""
Script to build the persistent FAISS RAG knowledge base for the AI Career Mentor.
Indexes career guides, roadmaps, and curated job corpus chunks.
Usage: python scripts/build_mentor_index.py [--force]
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
from src.parsing.loader import clean_text
from src.parsing.chunker import split_into_chunks
from src.search.embed import EmbeddingManager
from src.search.faiss_store import FaissVectorStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def build_mentor_index(force: bool = False):
    vector_store = FaissVectorStore(settings.MENTOR_INDEX_DIR)
    if vector_store.exists() and not force:
        logger.info(f"Mentor index already exists at {settings.MENTOR_INDEX_DIR}. Use --force to rebuild.")
        return

    all_chunks = []

    # 1. Ingest career notes
    career_dir = settings.CAREER_NOTES_DIR
    if career_dir.exists():
        for file_path in career_dir.glob("*.*"):
            if file_path.suffix.lower() in [".txt", ".md"]:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                cleaned = clean_text(content)
                metadata = {
                    "source_title": file_path.stem.replace("_", " ").title(),
                    "filename": file_path.name,
                    "doc_type": "career_guide",
                }
                chunks = split_into_chunks(cleaned, metadata=metadata, chunk_size=500, chunk_overlap=80)
                all_chunks.extend(chunks)
                logger.info(f"Loaded {len(chunks)} chunks from {file_path.name}")

    # 2. Ingest jobs corpus chunks
    jobs_csv = settings.JOBS_DATA_PATH
    if jobs_csv.exists():
        df = pd.read_csv(jobs_csv)
        for _, row in df.iterrows():
            job_text = (
                f"Job Title: {row.get('title', '')}\n"
                f"Company: {row.get('company', '')}\n"
                f"Location: {row.get('location', '')}\n"
                f"Skills: {row.get('skills', '')}\n"
                f"Description: {row.get('description', '')}"
            )
            metadata = {
                "source_title": f"Job Posting: {row.get('title', '')} ({row.get('company', '')})",
                "filename": f"job_{row.get('job_id', '')}.txt",
                "job_id": str(row.get("job_id", "")),
                "doc_type": "job_corpus",
            }
            chunks = split_into_chunks(job_text, metadata=metadata, chunk_size=450, chunk_overlap=60)
            all_chunks.extend(chunks)

    if not all_chunks:
        logger.error("No documents found to build mentor index.")
        sys.exit(1)

    logger.info(f"Total mentor chunks to index: {len(all_chunks)}")

    # Extract text strings and metadata mappings
    texts = [c["text"] for c in all_chunks]
    meta_list = [c["metadata"] for c in all_chunks]
    # Also attach full text and snippet into metadata for RAG context and citation display
    for i, meta in enumerate(meta_list):
        meta["text"] = texts[i]
        meta["snippet"] = texts[i][:200]

    logger.info(f"Generating embeddings for {len(texts)} chunks...")
    embed_manager = EmbeddingManager()
    vectors = embed_manager.embed_texts(texts)

    logger.info(f"Building FAISS mentor index with shape {vectors.shape}...")
    vector_store.build_index(vectors, meta_list)
    logger.info("Mentor RAG index successfully built and saved!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build FAISS Career Mentor knowledge base index.")
    parser.add_argument("--force", action="store_true", help="Force rebuild existing index")
    args = parser.parse_args()
    build_mentor_index(force=args.force)
