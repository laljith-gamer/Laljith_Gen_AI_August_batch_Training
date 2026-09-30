# SMART HIRE GENAI
### Resume Matching + AI Career Mentor with Human-in-the-Loop Verification & Grounded RAG

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Google GenAI SDK](https://img.shields.io/badge/Google%20GenAI%20SDK-v2.22.0-orange)](https://github.com/google-gemini/generative-ai-python)
[![Streamlit](https://img.shields.io/badge/Streamlit-v1.64.0-red)](https://streamlit.io/)
[![FAISS](https://img.shields.io/badge/FAISS-CPU%20v1.15.0-green)](https://github.com/facebookresearch/faiss)
[![Tests Passing](https://img.shields.io/badge/tests-46%20passed-brightgreen.svg)]() [![Live Demo](https://img.shields.io/badge/Live%20Demo-Streamlit%20Cloud-FF4B4B)](https://laljithgenaiaugustbatchtraining-iuuh9yklt3cca53wdrllml.streamlit.app/)

SmartHire GenAI is an end-to-end career intelligence portal that transforms candidate resumes into structured profiles with **Human-in-the-Loop (HITL) approval**, performs **dense semantic vector matching** against curated job postings using FAISS, generates **job-tailored CV improvements**, and provides an **AI Career Mentor** chatbot grounded in verified career roadmaps using **Retrieval-Augmented Generation (RAG)** and **Prompt Injection Guardrails**.

---

## Key Highlights & Core Principles

1. **Human-in-the-Loop (HITL) as a First-Class Citizen**:
   - Explicit state machine: `AI_GENERATED` $\to$ `REQUIRES_REVIEW` $\to$ `HUMAN_EDITED` $\to$ `APPROVED` $\to$ `REJECTED`.
   - The downstream semantic matching and CV improvement engines **strictly refuse execution** on raw AI output until a human reviewer has explicitly inspected, edited, and approved the profile.
2. **Gemini 3.8 Flash & Google GenAI SDK**:
   - Built on Google's modern official `google-genai` (v2.22.0) SDK.
   - Primary LLM: `gemini-3.8-flash` with automatic fallback to `gemini-3.6-flash` during peak demand spikes.
   - Embedding Model: `gemini-embedding-001` (3072 dimensions) with disk caching and local TF-IDF fallback.
3. **FAISS Vector Search**:
   - Persistent `IndexFlatIP` storing normalized cosine similarity vectors for job postings and career knowledge.
4. **Grounded AI Career Mentor (RAG)**:
   - Queries are grounded in curated career roadmaps and job postings.
   - Refuses ungrounded claims with: *"I don't know based on the available documents."*
   - Cites exact document names and chunk indices.
5. **Safety Guardrails & Prompt Injection Defense**:
   - Multi-layer defense blocking prompt injections, credential exfiltration, fake credentials, and off-topic requests while allowing legitimate career inquiries.
6. **Auditability & Zero Secret Exposure**:
   - Logs events to `data/feedback/audit.jsonl` with automatic credential scrubbing.

---

## System Architecture

```text
Resume Upload (PDF / DOCX)
        │
        ▼
Document Loader & Text Normalizer
        │
        ▼
Gemini 3.8 Flash Structured Parser (Pydantic Schema)
        │
        ▼
   ┌────────────────────────────────┐
   │ HUMAN-IN-THE-LOOP REVIEW (HITL)│
   │ State: REQUIRES_REVIEW         │
   │ Actions: Approve / Edit / Reset│
   └───────────────┬────────────────┘
                   │
                   ▼
         Approved Candidate Profile (APPROVED)
                   │
         ┌─────────┴────────────────────────┐
         │                                  │
         ▼                                  ▼
Profile Embedding                  Target Job Selection
(gemini-embedding-001)                      │
         │                                  ▼
         ▼                          CV Improvement Engine
FAISS Job Search                     (Gemini 3.8 Flash)
(IndexFlatIP - Cosine)                      │
         │                                  ▼
         ▼                         ┌───────────────────────────────┐
Top-N Semantic Job Matches         │ HUMAN-IN-THE-LOOP CV REVIEW   │
         │                         │ Actions: Accept / Edit /      │
Display & Relevance Feedback       │          Reject / Regenerate  │
(Relevant / Irrelevant)            └───────────────┬───────────────┘
                                                   │
                                                   ▼
                                         Final Tailored CV Plan

                                   ┌───────────────────────────────┐
                                   │ AI CAREER MENTOR (RAG)        │
                                   └───────────────┬───────────────┘
                                                   │
                                                   ▼
                                        Safety & Scope Guardrails
                                        (Prompt Injection Defense)
                                                   │
                                                   ▼
                                        Query Embedding & Retriever
                                        (FAISS Knowledge Index)
                                                   │
                                                   ▼
                                        Context Assembly & Grounding
                                                   │
                                                   ▼
                                        Gemini 3.8 Flash Generation
                                                   │
                                                   ▼
                                        Grounded Answer + Citations
                                                   │
                                                   ▼
                                        Human Feedback (Helpful / Not)
```

---

## Repository Directory Structure

```text
smarthire-genai/
├── README.md                          # Comprehensive project documentation
├── requirements.txt                   # Verified Python dependencies
├── .env.example                       # Environment configuration template
├── .gitignore                         # Git exclusion rules
├── LICENSE                            # MIT Open-Source License
│
├── memory/                            # Architectural memory & decisions
│   ├── architecture.md
│   ├── decisions.md
│   ├── progress.md
│   └── known_issues.md
│
├── data/
│   ├── jobs/
│   │   └── jobs.csv                   # Pre-collected curated job corpus (20 tech roles)
│   ├── resumes/
│   │   ├── sample_resume.pdf          # Demo candidate PDF resume
│   │   ├── sample_resume.docx         # Demo candidate DOCX resume
│   │   └── sample_resume.txt
│   ├── career_notes/                  # Knowledge base roadmaps & guides
│   │   ├── data_analyst_roadmap.txt
│   │   ├── backend_developer_roadmap.txt
│   │   ├── machine_learning_roadmap.txt
│   │   ├── cloud_engineer_roadmap.txt
│   │   ├── cybersecurity_roadmap.txt
│   │   ├── interview_preparation_guide.txt
│   │   └── resume_writing_guide.txt
│   └── feedback/                      # Persistent feedback & audit logs
│       ├── job_feedback.jsonl
│       ├── mentor_feedback.jsonl
│       └── audit.jsonl
│
├── vectorstore/
│   ├── embedding_cache.json           # Cached embeddings preventing redundant API costs
│   ├── jobs/                          # Persistent FAISS job index & metadata
│   │   ├── index.faiss
│   │   └── metadata.pkl
│   └── mentor/                        # Persistent FAISS career mentor RAG index
│       ├── index.faiss
│       └── metadata.pkl
│
├── scripts/
│   ├── validate_environment.py        # System health & dependency diagnostics
│   ├── build_job_index.py             # Preprocesses jobs and builds FAISS index
│   ├── build_mentor_index.py          # Chunks guides and builds mentor RAG index
│   └── create_demo_resumes.py         # Generates sample demo PDF/DOCX resumes
│
├── src/
│   ├── __init__.py
│   ├── config.py                      # Centralized configuration & Gemini client
│   ├── evaluate.py                    # Automated evaluation suite & benchmarks
│   │
│   ├── models/                        # Domain models & schemas
│   │   ├── __init__.py
│   │   ├── enums.py                   # WorkflowState, ReviewStatus, FeedbackRating
│   │   └── schemas.py                 # Pydantic ResumeProfile, JobPosting, CVSuggestion
│   │
│   ├── parsing/                       # Document ingestion & parsing
│   │   ├── __init__.py
│   │   ├── loader.py                  # PDF & DOCX extraction with whitespace cleanup
│   │   ├── chunker.py                 # Metadata-preserving recursive text chunker
│   │   └── resume_parser.py           # Gemini structured output parser
│   │
│   ├── search/                        # Vector embeddings & search
│   │   ├── __init__.py
│   │   ├── embed.py                   # EmbeddingManager with caching & local fallback
│   │   ├── faiss_store.py             # FAISS IndexFlatIP persistence wrapper
│   │   └── job_search.py              # Semantic job matching engine
│   │
│   ├── generate/                      # CV Improvement generation
│   │   ├── __init__.py
│   │   ├── prompts.py                 # Anti-hallucination prompt library
│   │   └── cv_suggestions.py          # Job-tailored CV suggestion engine
│   │
│   ├── mentor/                        # Grounded RAG Chatbot
│   │   ├── __init__.py
│   │   ├── prompts.py                 # Grounded RAG system prompt & refusal rules
│   │   ├── retriever.py               # Vector knowledge retriever
│   │   └── rag_chain.py               # End-to-end RAG inference chain
│   │
│   ├── safety/                        # Guardrails & Prompt Injection Defense
│   │   ├── __init__.py
│   │   └── guardrails.py              # Regex & semantic scope security classifier
│   │
│   └── human_loop/                    # Human-in-the-Loop workflows & telemetry
│       ├── __init__.py
│       ├── review.py                  # Profile review & diff computation
│       ├── feedback.py                # Telemetry logging & feedback metrics
│       └── audit.py                   # Secret-scrubbed audit logging
│
├── scripts/
│   ├── build_job_index.py                # FAISS index builder (dataset-mode aware)
│   ├── build_mentor_index.py             # Mentor RAG knowledge base builder
│   ├── download_kaggle_datasets.py       # Kaggle CLI dataset downloader
│   ├── prepare_kaggle_jobs.py            # Naukri raw → normalized pipeline
│   └── generate_report_pdf.py            # Report PDF generator
│
├── src/
│   ├── config.py                         # Settings, paths, dataset mode config
│   ├── evaluate.py                       # Evaluation suite with dataset reporting
│   ├── models/schemas.py                 # Pydantic models (JobPosting, ResumeProfile, etc.)
│   ├── search/
│   │   ├── embed.py                      # Gemini embeddings with caching
│   │   ├── faiss_store.py                # FAISS IndexFlatIP persistence
│   │   ├── job_search.py                 # Semantic job matching engine
│   │   └── job_repository.py             # Centralized job data access layer
│   ├── human_loop/                       # HITL approval state machine
│   ├── mentor/                           # RAG career mentor chain
│   ├── generate/                         # CV improvement engine
│   ├── safety/                           # Guardrails & prompt injection defense
│   └── parsing/                          # Resume document loaders
│
├── data/
│   ├── jobs/
│   │   ├── jobs_demo.csv                 # 20-role curated demo dataset
│   │   ├── jobs_kaggle_naukri.csv        # Normalized Kaggle Naukri corpus (generated)
│   │   └── dataset_metadata.json         # Pipeline metadata (generated)
│   ├── raw/kaggle/                       # Raw downloaded Kaggle files (not committed)
│   ├── career_notes/                     # RAG knowledge base documents
│   ├── feedback/                         # HITL feedback logs
│   └── resumes/                          # Sample resume documents
│
├── vectorstore/
│   ├── jobs/                             # FAISS job index + metadata
│   ├── mentor/                           # FAISS mentor index + metadata
│   └── embedding_cache.json             # Persistent embedding cache
│
├── app/
│   ├── streamlit_app.py                  # Main Streamlit application (with health checks)
│   ├── state.py                          # Reactive session state manager
│   └── components/                       # Modular Streamlit UI components
│       ├── profile_review.py
│       ├── job_cards.py                  # Job search (with dataset indicator)
│       ├── cv_review.py                  # Resume Studio (uses JobRepository)
│       └── mentor_chat.py
│
├── tests/                                # Automated test suite (Pytest)
│   ├── test_dataset_pipeline.py          # Dataset pipeline, modes, repository tests
│   ├── test_parser.py                    # Loader & Pydantic validation tests
│   ├── test_embeddings.py                # Embedding normalization & caching tests
│   ├── test_job_search.py                # FAISS retrieval & skill overlap tests
│   ├── test_human_loop.py                # State machine & approval enforcement tests
│   ├── test_guardrails.py                # Prompt injection & scope defense tests
│   ├── test_rag.py                       # RAG retrieval, citations & refusal tests
│   └── test_e2e_smoke.py                 # Full end-to-end user journey smoke test
│
└── reports/
    ├── evaluation_results.json           # Machine-readable benchmark telemetry
    └── answer_quality.md                 # Formatted evaluation & quality report
```

---

## Quick Start & Installation

### 1. Prerequisites
- Python 3.11 or 3.12
- Google Gemini API Key ([Get one free from Google AI Studio](https://aistudio.google.com/))

### 2. Environment Setup
```bash
# Clone the repository
git clone https://github.com/laljith-gamer/Laljith_Gen_AI_August_batch_Training.git
cd Laljith_Gen_AI_August_batch_Training/2nd\ month\ project

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install verified dependencies
pip install -r requirements.txt
```

### 3. Configure API Credentials
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` and set your key:
```ini
GEMINI_API_KEY=AIzaSy...your_gemini_api_key...
GEMINI_MODEL=gemini-3.8-flash
GEMINI_FALLBACK_MODEL=gemini-3.6-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
EMBEDDING_DIMENSION=3072
TOP_K_JOBS=5
```

### 4. Run Diagnostics
Verify packages, credentials, and paths:
```bash
python scripts/validate_environment.py
```

### 5. Build FAISS Vector Indexes
Build the pre-collected job index and mentor RAG knowledge base:
```bash
python scripts/build_job_index.py
python scripts/build_mentor_index.py
```

### 6. Launch the Streamlit Application
```bash
streamlit run app/streamlit_app.py
```
Open your browser at `http://localhost:8501`.

---

## Dataset Pipeline

The **primary job corpus** is the Kaggle Naukri dataset (`PromptCloudHQ/jobs-on-naukricom`), a pre-collected ~22,000-listing sample of Indian tech job postings. **Live scraping of LinkedIn/Naukri is NOT used.**

### Pipeline Flow

```text
Kaggle Naukri Dataset (PromptCloudHQ/jobs-on-naukricom)
    → Raw Download (scripts/download_kaggle_datasets.py --dataset naukri)
    → Raw Validation
    → Normalization (scripts/prepare_kaggle_jobs.py)
    → Prepared Job Corpus (data/jobs/jobs_kaggle_naukri.csv)
    → Gemini Embeddings (gemini-embedding-001, 3072 dims)
    → FAISS IndexFlatIP (scripts/build_job_index.py --force)
    → Semantic Job Search
    → Resume Studio
```

### Exact Commands

```bash
# Step 1: Download raw Kaggle dataset (requires Kaggle CLI authentication)
python scripts/download_kaggle_datasets.py --dataset naukri

# Step 2: Normalize raw dataset to application schema
python scripts/prepare_kaggle_jobs.py

# Step 3: Build FAISS semantic search index
python scripts/build_job_index.py --force

# Step 4: Set dataset mode in .env (defaults to raw_kaggle)
JOB_DATA_MODE=raw_kaggle

# Step 5: Launch application
streamlit run app/streamlit_app.py
```

### Dataset Modes

| Mode | Dataset | Jobs | Use Case |
|---|---|---|---|
| **`raw_kaggle`** (Default) | Kaggle Naukri normalized corpus | 21,739 | **Assignment / Production corpus** |
| `curated_demo` | 20 curated tech roles | 20 | Development / Unit testing only |

Set via `JOB_DATA_MODE` in `.env` or as an environment variable. **Default: `raw_kaggle`**.

The system does **NOT** silently fall back from `raw_kaggle` to the demo dataset. If the Kaggle corpus is not prepared, a clear diagnostic message is shown with exact commands to fix it.

### Column Mapping (Naukri Raw → App Schema)

| Raw Kaggle Column | Application Column |
|---|---|
| `jobtitle` | `title` |
| `company` | `company` |
| `joblocation_address` | `location` |
| `skills` | `skills` |
| `jobdescription` | `description` |
| `jobid` | `source_record_id` |

### Data Provenance

- Kaggle corpus rows: `source=kaggle_naukri`, `source_dataset=PromptCloudHQ/jobs-on-naukricom`
- Demo dataset rows: `source=curated_demo`

### External Kaggle Sources

| Dataset | Kaggle source | Local destination | Use |
|---|---|---|---|
| Resume Dataset | `snehaanbhawal/resume-dataset` | `data/raw/kaggle/resumes/` | Resume exploration |
| **Jobs on Naukri.com** | **`PromptCloudHQ/jobs-on-naukricom`** | **`data/raw/kaggle/jobs/`** | **Primary job corpus** |
| LinkedIn Job Postings | `arshkon/linkedin-job-postings` | `data/raw/kaggle/linkedin/` | Optional experiments |

Raw Kaggle files are stored separately under `data/raw/kaggle/` and are **not** committed to Git.
The normalization pipeline transforms raw data into `data/jobs/jobs_kaggle_naukri.csv` with the application's standard schema.

---

## Automated Testing & Evaluation

### Run Full Test Suite (24 Tests)
```bash
pytest tests/ -v
```

### Run End-to-End User Journey Smoke Test
```bash
python tests/test_e2e_smoke.py
```

### Run Evaluation Suite & Generate Reports
```bash
python -m src.evaluate
```
This benchmarks:
- **Retrieval Hit Rate**: Accuracy of Top-K FAISS retrieval against known job targets (Benchmark: **100%**).
- **Hallucination Refusal**: Verifies the model appropriately refuses questions unsupported by context (Benchmark: **100%**).
- **Prompt Comparison**: Analyzes grounded RAG output vs naive ungrounded prompts.
- **Human-in-the-Loop Telemetry**: Aggregates job relevance, mentor ratings, and CV suggestion actions.

---

## Guardrails & Prompt Injection Defense

SmartHire GenAI enforces defense-in-depth:
1. **Input Classification**: Detects and rejects prompt injection attempts (e.g. *"Ignore all previous instructions"*, *"DAN mode"*, *"Reveal system prompt"*), secret exfiltration (*"Print API key"*), and fraudulent requests (*"Fabricate a degree"*).
2. **Untrusted Data Boundary**: Resume text and retrieved knowledge chunks are strictly encapsulated in XML data delimiters:
   ```xml
   <untrusted_candidate_resume>...</untrusted_candidate_resume>
   <retrieved_context>...</retrieved_context>
   ```
   System instructions explicitly mandate treating content as raw data, not instructions.
3. **Traceable Citations**: Mentor outputs must reference exact filenames and chunk IDs from the knowledge base.

---

## Deployment Guide (Streamlit Community Cloud)

1. Push your repository to GitHub (ensure `.env` and `__pycache__` are excluded via `.gitignore`).
2. Log in to [Streamlit Community Cloud](https://share.streamlit.io/).
3. Connect your repository and select `app/streamlit_app.py` as the main entrypoint.
4. Under **Advanced Settings > Secrets**, configure:
   ```toml
   GEMINI_API_KEY = "your_gemini_api_key"
   GEMINI_MODEL = "gemini-3.8-flash"
   GEMINI_FALLBACK_MODEL = "gemini-3.6-flash"
   GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"
   EMBEDDING_DIMENSION = 3072
   ```
5. Deploy! The vector store indexes will load seamlessly from the repository.

**Live Demo:** [https://laljithgenaiaugustbatchtraining-iuuh9yklt3cca53wdrllml.streamlit.app/](https://laljithgenaiaugustbatchtraining-iuuh9yklt3cca53wdrllml.streamlit.app/)

---

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
