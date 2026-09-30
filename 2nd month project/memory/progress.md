# SmartHire GenAI - Implementation Progress

## Phase Tracking
- [x] **PHASE 0**: Workspace inspection, environment, memory initialization.
- [x] **PHASE 1**: Environment, configuration, Gemini connectivity, document loaders.
- [x] **PHASE 2**: Resume parser, Pydantic schemas, structured JSON output.
- [x] **PHASE 3**: Human profile review state machine, approval/edit/reject workflows.
- [x] **PHASE 4**: Job dataset preprocessing, embedding generation, FAISS index creation.
- [x] **PHASE 5**: Semantic job matching engine, Top-N ranking, relevance feedback.
- [x] **PHASE 6**: CV improvement generator, anti-hallucination constraints, human CV review.
- [x] **PHASE 7**: Career knowledge base curation, chunking, RAG vector indexing.
- [x] **PHASE 8**: AI Career Mentor, RAG retrieval chain, source citations.
- [x] **PHASE 9**: Guardrails layer, prompt injection defense, adversarial tests.
- [x] **PHASE 10**: Evaluation suite (retrieval hit rate, grounding, hallucination test).
- [x] **PHASE 11**: Streamlit web application with multi-tab workflow.
- [x] **PHASE 12**: Automated test suite, bug fixes, end-to-end verification.
- [x] **PHASE 13**: README, documentation, deployment preparation.
- [x] **PHASE 14**: Live deployment to Streamlit Community Cloud.
- [x] **PHASE 15**: Final report PDF generation.
- [x] **PHASE 16**: Embedding model comparison notebook.
- [x] **PHASE 17**: Tailored resume DOCX download.
- [x] **PHASE 18**: **Kaggle Naukri Dataset Pipeline Integration & Hardening**
  - Download & integrity pipeline (`scripts/download_kaggle_datasets.py`)
  - Full dataset audit & normalization pipeline (`scripts/prepare_kaggle_jobs.py`): 22,000 raw → 21,739 clean normalized postings
  - Strict dataset modes (`JOB_DATA_MODE=raw_kaggle` default, no silent fallback to demo)
  - Resumable streaming batch embedding (`src/search/embed.py`): batch size 25, per-batch on-disk caching, 429 exponential backoff
  - Full-corpus FAISS index builder (`scripts/build_job_index.py`): defaults to entire 21,739 corpus; supports `--limit N` for development/testing; tracks partial status in `index_metadata.json`
  - Centralized job data access layer (`src/search/job_repository.py`) with high-performance substring query search across 21,739 jobs
  - UI modernization: Streamlit searchable role selector in `cv_review.py` (prevents 21,739-row DOM freeze), production dataset badges in `job_cards.py`
  - Hybrid skill overlap calculation in `src/search/job_search.py` (checks skills column + title/description)
  - Dynamic evaluation reporting in `src/evaluate.py` reflecting active dataset mode, corpus size, and index status
  - 20-test dataset pipeline suite (`tests/test_dataset_pipeline.py`) — 35/35 test suite passing

## Current Dataset Status
- **Production Corpus**: Kaggle Naukri (`PromptCloudHQ/jobs-on-naukricom`)
  - File: `data/jobs/jobs_kaggle_naukri.csv`
  - Rows: 21,739 clean normalized jobs
  - Hash: `c12e3f6eee81f5e98371b487d031fdaa`
- **Development/Test Demo Corpus**: 20 curated roles (`data/jobs/jobs_demo.csv`)
- **Active Mode**: `raw_kaggle` (controlled via `JOB_DATA_MODE` env var)
- **FAISS Vector Store**: `vectorstore/jobs/` (includes `index.faiss`, `metadata.pkl`, `index_metadata.json`)

## Exact Pipeline Reproduction Commands
```bash
# 1. Download raw Kaggle dataset archive (if not already downloaded)
python scripts/download_kaggle_datasets.py --dataset naukri

# 2. Normalize raw Kaggle data to application schema (21,739 records)
python scripts/prepare_kaggle_jobs.py

# 3. Build FAISS index (default: builds entire active corpus)
# Note: For fast testing under Gemini Free Tier quota (100 items/min), use --limit 500
python scripts/build_job_index.py --force

# 4. Verify test suite (20 pipeline tests, 35 total tests)
pytest tests/test_dataset_pipeline.py -v
pytest tests/ -v

# 5. Run evaluation report
python src/evaluate.py

# 6. Launch production Streamlit application
streamlit run app/streamlit_app.py
```
