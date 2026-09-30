# SmartHire GenAI - Architectural & Design Decisions

## 1. LLM & SDK Selection
- **Decision**: Use `google-genai` (version 2.22.0) with primary model `gemini-3.5-flash-lite`.
- **Rationale**: `google-genai` is Google's official modern SDK.
- **Fallback**: Implemented automatic fallback during peak demand spikes.

## 2. Embedding Model & Vector Index
- **Decision**: Use `gemini-embedding-001` (dimension: 3072) with FAISS `IndexFlatIP` (normalized cosine similarity).
- **Caching**: Embedding cache (in-memory + disk persistent) prevents redundant API calls.
- **Offline/Fallback**: Local TF-IDF cosine vectorizer fallback for zero crashes without API key.

## 3. Human-in-the-Loop (HITL) as Core Architecture
- **Decision**: First-class state machine: `AI_GENERATED` -> `REQUIRES_REVIEW` -> `HUMAN_EDITED` -> `APPROVED` -> `REJECTED`.
- **Enforcement**: Downstream pipelines strictly require `HumanApprovedProfile` with `status == APPROVED`.

## 4. Primary Job Corpus: Kaggle Naukri Dataset
- **Decision**: Use `PromptCloudHQ/jobs-on-naukricom` (~22K listings) as the primary job corpus.
- **Rationale**: Assignment specification requires pre-collected Kaggle dataset. Live scraping is NOT allowed.
- **Curated Demo**: The original 20-role dataset is retained as `curated_demo` mode for fast testing.
- **Dataset Modes**: `JOB_DATA_MODE` controls which corpus is active (`raw_kaggle` vs `curated_demo`).
- **No Silent Fallback**: System does NOT silently substitute demo data when raw_kaggle mode is selected.

## 5. Dataset Normalization Pipeline
- **Decision**: Dedicated `scripts/prepare_kaggle_jobs.py` normalizes raw Kaggle columns to app schema.
- **Column Mapping**: `jobtitle` → `title`, `joblocation_address` → `location`, `jobdescription` → `description`, etc.
- **Provenance**: Every normalized row tagged with `source=kaggle_naukri` and `source_dataset=PromptCloudHQ/jobs-on-naukricom`.
- **Deduplication**: Deterministic MD5-based key from normalized title+company+location+description.

## 6. Centralized Job Repository
- **Decision**: `src/search/job_repository.py` provides a single source of truth for job data.
- **Rationale**: Prevents Resume Studio and Job Search from using different datasets.
- **Health Checks**: Dataset availability, index staleness, and mode validation.

## 7. FAISS Index Versioning
- **Decision**: Store `index_metadata.json` alongside the FAISS index with dataset hash.
- **Rationale**: Prevents stale indexes from returning results from a different dataset version.
- **Auto-rebuild**: Index is automatically rebuilt when dataset hash mismatch is detected.

## 8. RAG Knowledge Base & Refusal Design
- **Decision**: RAG retriever indexes job postings and curated career roadmaps.
- **Citations**: All responses list exact source document names and chunk indices.

## 9. Guardrails & Prompt Injection Defense
- **Decision**: Two-tier safety: input classifier + data/instruction boundary enforcement.
