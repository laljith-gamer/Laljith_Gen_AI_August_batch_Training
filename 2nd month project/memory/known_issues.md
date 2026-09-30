# SmartHire GenAI - Known Issues & Mitigations

## 1. Gemini Preview 503 Spikes
- **Issue**: Google preview models can occasionally return `503 UNAVAILABLE` during peak demand.
- **Mitigation**: Automatic retry with exponential backoff and fallback model.

## 2. Global Python Torchaudio DLL Error
- **Issue**: Broken torchaudio DLL conflict in global Python environment.
- **Mitigation**: Use project's dedicated virtual environment.

## 3. Gemini Embedding 001 Dimensions
- **Issue**: `gemini-embedding-001` returns 3072-dimensional vectors.
- **Mitigation**: FAISS index dimension configured dynamically to match embedding output.

## 4. Raw Kaggle Dataset Not Auto-Downloaded
- **Issue**: The raw Kaggle Naukri dataset (~22K listings) is not included in the repository and must be downloaded separately.
- **Mitigation**: Clear diagnostic messages when dataset is missing. Curated demo mode available as fallback.
- **Command**: `python scripts/download_kaggle_datasets.py --dataset naukri`

## 5. Dataset Size for Git/Deployment
- **Issue**: The normalized Kaggle corpus may be too large for Git commits or Streamlit Community Cloud.
- **Mitigation**: `--max-rows` flag in prepare_kaggle_jobs.py allows creating a size-constrained subset.
- **Note**: The curated_demo mode can be used for deployment when full corpus is impractical.

## 6. Embedding Cost for Large Datasets
- **Issue**: Embedding 22K job descriptions with Gemini API incurs significant API calls.
- **Mitigation**: Embedding cache (`vectorstore/embedding_cache.json`) persists embeddings across runs.
- **Note**: Initial embedding of full corpus requires sufficient API quota.

## 7. FAISS Index Staleness (RESOLVED)
- **Issue**: Previously, FAISS indexes could become stale when the job dataset changed.
- **Fix**: Index versioning via `index_metadata.json` with dataset hash comparison. Auto-rebuild on mismatch.

## 8. Resume Studio Hardcoded Dataset Path (RESOLVED)
- **Issue**: `cv_review.py` previously hardcoded `data/jobs/jobs.csv`.
- **Fix**: Now uses centralized `JobRepository.load_active_jobs()` for dataset-mode-aware loading.
