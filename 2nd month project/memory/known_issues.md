# SmartHire GenAI - Known Issues & Mitigations

## 1. Gemini Preview 503 Spikes
- **Issue**: Google preview models can occasionally return `503 UNAVAILABLE` during peak demand.
- **Mitigation**: Automatic retry with exponential backoff and fallback model (`gemini-2.5-flash`).

## 2. Gemini API Free Tier Embedding Rate Limits (100 items / min)
- **Issue**: The Free Tier quota for `gemini-embedding-001` restricts embedding requests to 100 items per minute (`generativelanguage.googleapis.com/embed_content_free_tier_requests`). Attempting to embed all 21,739 jobs in one non-resumable run triggers HTTP 429 (`RESOURCE_EXHAUSTED`).
- **Mitigation**:
  1. **Resumable Streaming Batching**: `EmbeddingManager.embed_texts` processes texts in batches of 25 and incrementally writes to `vectorstore/embedding_cache.json` after every batch.
  2. **Zero Vector Loss**: If interrupted or quota-throttled, rerunning `python scripts/build_job_index.py` resumes from the last completed batch without duplicate API calls.
  3. **Quota Backoff**: Automatically catches 429 errors and pauses with backoff before retrying.
  4. **Explicit Flag `--limit N`**: For local verification, CI/CD, or development, `python scripts/build_job_index.py --limit 500` creates a verified partial index without consuming full API quotas.
  5. **Transparent Metadata**: `index_metadata.json` explicitly flags `is_partial_index: true/false` and records `indexed_job_count` vs `total_dataset_rows`.

## 3. Large Dataset UI Rendering Bottlenecks
- **Issue**: Populating a Streamlit `st.selectbox` with all 21,739 job postings results in an ~80MB browser DOM, freezing browser tabs and causing UI unresponsiveness.
- **Mitigation**: In `app/components/cv_review.py`, replaced the giant selectbox with:
  - An instant text search input calling `JobRepository.search_jobs_by_query(query, limit=50)`
  - A default list of top representative industry roles (`JobRepository.get_popular_target_jobs(limit=50)`)
  - Candidates can search and select from the full 21,739 jobs in milliseconds without browser lag.

## 4. Skills Column vs Description in Raw Kaggle Data
- **Issue**: In the raw Kaggle Naukri dataset, the `skills` column frequently contains broad functional category strings (e.g. `IT Software - Application Programming`) rather than individual tech skills like `Python`, `SQL`, or `Power BI`.
- **Mitigation**: In `src/search/job_search.py`, `calculate_skill_overlap` checks for candidate skills against both the `skills` list and the combined `f"{job.title} {job.description}"` text.

## 5. Raw Kaggle Dataset Download
- **Issue**: The raw Kaggle archive (`data/raw/kaggle/jobs/naukri_com-job_sample.csv`) is 62 MB and gitignored to keep the git repository lightweight.
- **Mitigation**: Automated download script (`scripts/download_kaggle_datasets.py --dataset naukri`) handles downloading or extracting. `scripts/prepare_kaggle_jobs.py` provides detailed guidance if the raw archive is missing.

## 6. FAISS Index Staleness (RESOLVED)
- **Issue**: Previously, rebuilding the index was manual, and changes to the underlying CSV could produce stale vector lookups.
- **Fix**: Implemented `index_metadata.json` with dataset hash tracking and automatic rebuild prompts/triggers.

## 7. Resume Studio Data Source Decoupling (RESOLVED)
- **Issue**: Resume Studio previously hardcoded `data/jobs/jobs.csv`.
- **Fix**: Centralized through `JobRepository.load_active_jobs()` and `JobRepository.get_popular_target_jobs()`, ensuring both Job Search and Resume Studio operate on identical, mode-aware data sources.
