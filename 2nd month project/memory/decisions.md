# SmartHire GenAI - Architectural & Design Decisions

## 1. LLM & SDK Selection
- **Decision**: Use `google-genai` (version 2.22.0) with primary model `gemini-3.8-flash`.
- **Rationale**: `google-genai` is Google's official modern SDK. `gemini-3.8-flash` is actively supported on the user's API key.
- **Fallback**: Implemented automatic fallback to `gemini-3.6-flash` if 503 high-demand temporary spikes occur on preview endpoints.

## 2. Embedding Model & Vector Index
- **Decision**: Use `gemini-embedding-001` (dimension: 3072) with FAISS `IndexFlatIP` (normalized cosine similarity).
- **Caching**: Implemented an embedding cache (in-memory + disk persistent) to prevent redundant Gemini API calls during testing and rerun loops.
- **Offline/Fallback**: Included a local TF-IDF / character n-gram cosine vectorizer fallback to ensure zero crashes if the user runs without an API key or when network connectivity is restricted.

## 3. Human-in-the-Loop (HITL) as Core Architecture
- **Decision**: First-class state machine: `AI_GENERATED` -> `REQUIRES_REVIEW` -> `HUMAN_EDITED` -> `APPROVED` -> `REJECTED`.
- **Enforcement**: Downstream job matching and CV improvement pipelines strictly require a `HumanApprovedProfile` with `status == APPROVED`. Raw AI parser output cannot bypass human review.
- **Auditing**: All changes between AI original output and human edits are diffed, summarized, and logged to `data/feedback/audit.jsonl`.

## 4. RAG Knowledge Base & Refusal Design
- **Decision**: RAG retriever indexes job postings and curated career roadmaps (`data/career_notes/`).
- **Prompt Engineering**: The mentor is strictly instructed to answer only from retrieved chunks for factual statements. If the context is missing or insufficient, the model must explicitly respond: *"I don't know based on the available documents."*
- **Citations**: All responses must list exact source document names and chunk indices.

## 5. Guardrails & Prompt Injection Defense
- **Decision**: Two-tier safety:
  1. Input classifier rejecting prompt injection ("ignore previous instructions", "print system prompt"), secret exfiltration, fake credential fabrication, and off-topic requests.
  2. Data vs Instruction encapsulation: Uploaded resume text and retrieved RAG context are encapsulated in XML data delimiters `<untrusted_candidate_resume>` and `<retrieved_context>`, explicitly instructing the model that contents are data, not instructions.
