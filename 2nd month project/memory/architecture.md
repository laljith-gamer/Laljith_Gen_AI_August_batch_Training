# SmartHire GenAI - System Architecture

## Overview
SmartHire GenAI is an end-to-end career intelligence portal designed to provide resume parsing with Human-in-the-Loop (HITL) approval, semantic job matching using FAISS vector search, AI-driven CV improvement recommendations, and a grounded AI Career Mentor chatbot using Retrieval-Augmented Generation (RAG).

## Dataset Pipeline Architecture
```text
Kaggle Naukri Dataset (PromptCloudHQ/jobs-on-naukricom)
        │
        ▼
Raw Dataset Download (scripts/download_kaggle_datasets.py)
        │  • Validates SHA-256 / archive integrity
        │  • Extracts to data/raw/kaggle/jobs/
        ▼
data/raw/kaggle/jobs/naukri_com-job_sample.csv (22,000 raw postings)
        │
        ▼
Normalization Pipeline (scripts/prepare_kaggle_jobs.py)
  • Column mapping (jobtitle→title, joblocation_address→location, etc.)
  • Text cleaning (HTML tag removal, entity decoding, whitespace normalization)
  • Invalid row filtering (removes empty or short descriptions < 20 chars; 4 dropped)
  • Deduplication (deterministic MD5 key on title+company+location+description; 257 removed)
  • Provenance tagging (source=kaggle_naukri, source_dataset=PromptCloudHQ/jobs-on-naukricom)
        │
        ▼
data/jobs/jobs_kaggle_naukri.csv (21,739 normalized application-ready corpus)
        │
        ▼
Resumable Embedding Generation (gemini-embedding-001, 3072 dims)
  • Streaming batch embedding (batch_size=25)
  • Incremental on-disk caching (vectorstore/embedding_cache.json saved after each batch)
  • Rate limit & quota backoff (handles 429 RESOURCE_EXHAUSTED with exponential sleep)
        │
        ▼
FAISS IndexFlatIP (scripts/build_job_index.py)
  • Default: indexes entire active corpus (21,739 jobs)
  • Optional: --limit N for fast development / testing
  • Index metadata & versioning (dataset hash, staleness detection, is_partial_index)
  • Portable relative paths (data/jobs/jobs_kaggle_naukri.csv)
        │
        ▼
vectorstore/jobs/ (index.faiss + metadata.pkl + index_metadata.json)
        │
        ▼
Semantic Job Search (src/search/job_search.py)
  • Cosine similarity via FAISS
  • Hybrid skill overlap scoring (checks skills column + job title/description)
  • Relevance explanations and score breakdown
        │
        ▼
Resume Matching → Resume Studio
  • Scalable target role search (JobRepository.search_jobs_by_query) across all 21,739 jobs
  • Popular role suggestions (JobRepository.get_popular_target_jobs)
  • Zero UI lag with full corpus searchability
```

## Dataset Modes
- **raw_kaggle**: Uses the Kaggle Naukri normalized corpus (21,739 listings). Strict mode — never silently falls back to demo data.
- **curated_demo**: Uses the 20-role demo dataset (`data/jobs/jobs_demo.csv`) strictly for unit tests and local dev without full data.
- Controlled via `JOB_DATA_MODE` environment variable (`raw_kaggle` is production default).
- Both modes use the same centralized FAISS pipeline and repository interface.

## Centralized Job Access
- `src/search/job_repository.py`: Single source of truth for job data.
- Used by Job Search, Resume Studio, Evaluation, and UI components.
- Provides dataset health checks, staleness detection, and scalable substring search across 21K+ records.

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
         │                              │
         ▼                              ▼
Profile Embedding              Target Job Selection
(gemini-embedding-001)         (from 21,739 Kaggle corpus via JobRepository)
         │                              │
         ▼                              ▼
FAISS Job Search               CV Improvement Engine
(IndexFlatIP - Cosine)         (Gemini)
         │                              │
         ▼                              ▼
Top-N Semantic Matches         HITL CV Review
         │
         ▼
Relevance Feedback
```

## Subsystems
1. **Resume Parser**: Multi-format document loading, Pydantic structured output validation.
2. **HITL Profile Review**: Explicit state machine preventing unapproved data propagation.
3. **Embeddings & Vector Store**: `gemini-embedding-001` (3072 dims) with caching; persistent FAISS index.
4. **Job Data Repository**: Centralized access layer supporting dataset modes, scalable search, and health checks.
5. **Semantic Job Search**: FAISS queries with cosine similarity, skill overlap, and explanations.
6. **CV Improvement Studio**: Job-targeted improvements with anti-hallucination constraints.
7. **AI Career Mentor**: RAG chatbot grounded in career roadmaps with citations.
8. **Guardrails & Security**: Prompt injection defense and scope validation.
9. **Evaluation Suite**: Automated tests for retrieval, grounding, and dataset validation.
10. **Streamlit UI**: Interactive dashboard with production dataset badges and live health monitoring.
