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
- [x] **PHASE 18**: **Kaggle Naukri Dataset Pipeline Integration**
  - Normalization pipeline (`scripts/prepare_kaggle_jobs.py`)
  - Centralized job repository (`src/search/job_repository.py`)
  - Dataset modes (`JOB_DATA_MODE`: raw_kaggle / curated_demo)
  - FAISS index versioning and staleness detection
  - Resume Studio unified data source
  - Startup health checks
  - Test suite for dataset pipeline
  - Updated evaluation with dataset reporting
  - Curated 20-role dataset retained as demo/test corpus

## Current Dataset Status
- **Primary corpus**: Kaggle Naukri (`PromptCloudHQ/jobs-on-naukricom`)
- **Demo corpus**: 20 curated tech roles (`data/jobs/jobs_demo.csv`)
- **Active mode**: Determined by `JOB_DATA_MODE` environment variable
- **Raw Kaggle data**: Must be downloaded separately via `scripts/download_kaggle_datasets.py`

## Exact Pipeline Commands
```bash
# 1. Download raw Kaggle data
python scripts/download_kaggle_datasets.py --dataset naukri

# 2. Normalize to application schema
python scripts/prepare_kaggle_jobs.py

# 3. Build FAISS index
python scripts/build_job_index.py --force

# 4. Set dataset mode
set JOB_DATA_MODE=raw_kaggle  # or curated_demo

# 5. Launch application
streamlit run app/streamlit_app.py
```
