# SmartHire GenAI - Architectural & Design Decisions

## 1. LLM & SDK Selection
- **Decision**: Use `google-genai` (version 2.22.0) with primary model `gemini-3.5-flash-lite`.
- **Rationale**: `google-genai` is Google's official modern SDK.
- **Fallback**: Implemented automatic fallback during peak demand spikes.

## 2. Embedding Model & Vector Index
- **Decision**: Use `gemini-embedding-001` (dimension: 3072) with FAISS `IndexFlatIP` (normalized cosine similarity).
- **Caching**: Embedding cache (in-memory + disk persistent at `vectorstore/embedding_cache.json`) prevents redundant API calls.
- **Offline/Fallback**: Local TF-IDF cosine vectorizer fallback for zero crashes without API key.

## 3. Human-in-the-Loop (HITL) as Core Architecture
- **Decision**: First-class state machine: `AI_GENERATED` -> `REQUIRES_REVIEW` -> `HUMAN_EDITED` -> `APPROVED` -> `REJECTED`.
- **Enforcement**: Downstream pipelines strictly require `HumanApprovedProfile` with `status == APPROVED`.

## 4. Primary Job Corpus: Kaggle Naukri Dataset
- **Decision**: Use `PromptCloudHQ/jobs-on-naukricom` (21,739 normalized listings) as the primary production job corpus.
- **Rationale**: Assignment specification requires pre-collected Kaggle dataset. Live scraping is strictly NOT allowed.
- **Curated Demo**: The original 20-role dataset is retained as `curated_demo` mode for unit tests and local mock runs.
- **Dataset Modes**: `JOB_DATA_MODE` controls which corpus is active (`raw_kaggle` vs `curated_demo`).
- **No Silent Fallback**: In `raw_kaggle` mode, the system raises an explicit `FileNotFoundError` with remediation steps rather than silently substituting demo data.

## 5. Dataset Normalization Pipeline
- **Decision**: Dedicated `scripts/prepare_kaggle_jobs.py` normalizes raw Kaggle columns to app schema.
- **Column Mapping**: `jobtitle` → `title`, `joblocation_address` → `location`, `jobdescription` → `description`, `skills` → `skills`, `jobid` → `source_record_id`.
- **Provenance**: Every normalized row tagged with `source=kaggle_naukri` and `source_dataset=PromptCloudHQ/jobs-on-naukricom`.
- **Deduplication**: Deterministic MD5 key from normalized `title|company|location|description[:500]`.
- **Audit Results**: 22,000 raw → 4 filtered (< 20 char desc) → 257 duplicates dropped → 21,739 clean normalized postings.

## 6. Centralized Job Repository & UI Performance
- **Decision**: `src/search/job_repository.py` provides a single source of truth for job data across Job Search and Resume Studio.
- **Scalable UI Lookup**: Loading 21,739 full objects into a Streamlit `st.selectbox` causes extreme browser DOM lag and memory bottlenecks (~80MB DOM tree).
- **Solution**: Implemented `JobRepository.search_jobs_by_query(query, limit=50)` and `get_popular_target_jobs(limit=50)` so candidates can search any of the 21,739 roles via an instant search box, or pick from top popular roles, with zero UI freezing.

## 7. Resumable Batch Embedding & API Rate Limits
- **Decision**: Embeddings are computed in streaming batches of 25 items and saved incrementally to disk after every single batch.
- **Rationale**: Gemini API Free Tier enforces a quota limit of 100 embed requests/items per minute. Embedding 21,739 items in one shot fails with HTTP 429 (`RESOURCE_EXHAUSTED`).
- **Resilience**: With per-batch disk persistence, interruption at any point preserves all completed embeddings. Rerunning `build_job_index.py` reads from cache and resumes instantly without duplicate API calls or costs.
- **Backoff**: Automatic retry with exponential backoff on HTTP 429 errors.

## 8. FAISS Index Versioning & Partial vs Full Reporting
- **Decision**: Store `index_metadata.json` alongside the FAISS index with dataset hash, row count, indexed count, and `is_partial_index` flag.
- **Rationale**: Prevents stale indexes and provides complete transparency. If an index is built with `--limit 500` for development or quota testing, it is explicitly labeled as `PARTIAL / DEVELOPMENT` with exact counts (e.g. 500 / 21,739), never misrepresenting partial indices as full corpus.
- **Auto-rebuild**: Rebuilds automatically when dataset hash mismatch is detected or when upgrading from a partial index to a full build without `--limit`.
- **Portability**: All file paths stored in metadata are relative to project root (`data/jobs/...`), enabling index portability across environments.

## 9. RAG Knowledge Base & Refusal Design
- **Decision**: RAG retriever indexes job postings and curated career roadmaps.
- **Citations**: All responses list exact source document names and chunk indices.

## 10. Guardrails & Prompt Injection Defense
- **Decision**: Two-tier safety: input classifier + data/instruction boundary enforcement.
