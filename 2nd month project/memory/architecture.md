# SmartHire GenAI - System Architecture

## Overview
SmartHire GenAI is an end-to-end career intelligence portal designed to provide resume parsing with Human-in-the-Loop (HITL) approval, semantic job matching using FAISS vector search, AI-driven CV improvement recommendations, and a grounded AI Career Mentor chatbot using Retrieval-Augmented Generation (RAG).

## Dataset Pipeline Architecture
```text
Kaggle Naukri Dataset (PromptCloudHQ/jobs-on-naukricom)
        │
        ▼
Raw Dataset Download (scripts/download_kaggle_datasets.py)
        │
        ▼
data/raw/kaggle/jobs/naukri_com-job_sample.csv
        │
        ▼
Normalization Pipeline (scripts/prepare_kaggle_jobs.py)
  • Column mapping (jobtitle→title, joblocation_address→location, etc.)
  • Text cleaning (HTML removal, whitespace normalization)
  • Duplicate removal (deterministic MD5 key)
  • Provenance tagging (source=kaggle_naukri)
        │
        ▼
data/jobs/jobs_kaggle_naukri.csv (normalized application-ready corpus)
        │
        ▼
Embedding Generation (gemini-embedding-001, 3072 dims)
        │
        ▼
FAISS IndexFlatIP (scripts/build_job_index.py)
  • Index versioning (dataset hash, staleness detection)
  • Metadata persistence (metadata.pkl + index_metadata.json)
        │
        ▼
vectorstore/jobs/ (index.faiss + metadata.pkl + index_metadata.json)
        │
        ▼
Semantic Job Search (src/search/job_search.py)
        │
        ▼
Resume Matching → Resume Studio
```

## Dataset Modes
- **raw_kaggle**: Uses the Kaggle Naukri normalized corpus (~22K listings)
- **curated_demo**: Uses the 20-role demo dataset for testing/development
- Controlled via `JOB_DATA_MODE` environment variable
- Both modes use the same FAISS pipeline and job repository

## Centralized Job Access
- `src/search/job_repository.py`: Single source of truth for job data
- Used by Job Search, Resume Studio, and Evaluation
- Provides dataset health checks and staleness detection

## High-Level Architecture Flow
```text
Resume Upload (PDF/DOCX)
        │
        ▼
Document Loader & Normalization
        │
        ▼
Gemini Structured Parser (Pydantic Schema)
        │
        ▼
   ┌────────────────────────────────┐
   │ HUMAN-IN-THE-LOOP REVIEW       │
   │ State: REQUIRES_REVIEW         │
   │ Actions: Approve / Edit / Reset│
   └────────────────┬───────────────┘
                   │
                   ▼
         Approved Candidate Profile
                   │
         ┌─────────┴────────────────────┐
         │                                  │
         ▼                                  ▼
Profile Embedding                  Target Job Selection
(gemini-embedding-001)             (from active job corpus)
         │                                  │
         ▼                                  ▼
FAISS Job Search                   CV Improvement Engine
(IndexFlatIP - Cosine)             (Gemini)
         │                                  │
         ▼                                  ▼
Top-N Semantic Matches             HITL CV Review
         │
         ▼
Relevance Feedback
```

## Subsystems
1. **Resume Parser**: Multi-format document loading, Pydantic structured output validation.
2. **HITL Profile Review**: Explicit state machine preventing unapproved data propagation.
3. **Embeddings & Vector Store**: `gemini-embedding-001` (3072 dims) with caching; persistent FAISS index.
4. **Job Data Repository**: Centralized access layer supporting dataset modes and health checks.
5. **Semantic Job Search**: FAISS queries with cosine similarity, skill overlap, and explanations.
6. **CV Improvement Studio**: Job-targeted improvements with anti-hallucination constraints.
7. **AI Career Mentor**: RAG chatbot grounded in career roadmaps with citations.
8. **Guardrails & Security**: Prompt injection defense and scope validation.
9. **Evaluation Suite**: Automated tests for retrieval, grounding, and dataset validation.
10. **Streamlit UI**: Interactive dashboard with dataset health indicators.
