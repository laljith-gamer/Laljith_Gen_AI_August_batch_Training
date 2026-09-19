# SmartHire GenAI - Known Issues & Mitigations

## 1. Gemini Preview 503 Spikes
- **Issue**: Google preview models (such as `gemini-3.8-flash`) can occasionally return `503 UNAVAILABLE` during peak demand spikes.
- **Mitigation**: Implemented automatic retry with exponential backoff and a configurable fallback model (`gemini-3.6-flash`).

## 2. Global Python Torchaudio DLL Error
- **Issue**: The global system python environment in `AppData/Roaming/Python/Python311` has a broken torchaudio DLL conflict (`libtorchaudio.pyd`).
- **Mitigation**: Use the project's dedicated virtual environment (`c:\Users\ASUS\Desktop\personal\genai-inter\venv`) which does not rely on `torchaudio` and executes `google-genai`, `faiss`, `streamlit`, `pandas`, `pypdf`, and `python-docx` seamlessly.

## 3. Gemini Embedding 001 Dimensions
- **Issue**: `gemini-embedding-001` returns 3072-dimensional vectors instead of older 768-dimensional models.
- **Mitigation**: Configured FAISS index dimension dynamically to match the embedding model output vector dimension (`3072`), with metadata storing dimensions.

## 4. Fallback Parser Heading Extraction (FIXED)
- **Issue**: When both Gemini models returned 503, the deterministic `fallback_regex_parser()` used `lines[2]` for the summary field, which grabbed section heading labels (e.g. "CAREER OBJECTIVE") instead of the actual paragraph content beneath them. It also set `target_role` to the contact info line and `years_of_experience` to None.
- **Fix** (2026-09-19): Rewrote `fallback_regex_parser()` with:
  - `_is_section_heading()`: Detects known resume section headings by keyword set + ALL-CAPS heuristic, with smart name-vs-heading disambiguation.
  - `_extract_sections()`: Parses resume into heading-keyed section dictionary.
  - Summary now extracted from the paragraph content under CAREER OBJECTIVE/PROFESSIONAL SUMMARY headings.
  - Target role inferred from domain keywords in the resume text.
  - Years of experience estimated from date ranges (e.g. "2023 - 2027").
  - Education items properly extracted with correct EducationItem schema fields.
  - Expanded skills vocabulary (21 → 40+ keywords including Flutter, Dart, NLP, etc.).

## 5. RAG Mentor Chunk Truncation & Multi-Turn Chat Stuck (FIXED)
- **Issue**:
  1. In `scripts/build_mentor_index.py`, metadata stored only `snippet` (truncated to 200 characters) and omitted `text`. This caused RAG context to be cut off mid-sentence (e.g. for the STAR interview method, only "Situation: Set the scene, c" was passed to Gemini), leading to unwarranted hallucination refusals.
  2. In `app/components/mentor_chat.py`, there was no "Clear Chat" or "New Chat" button, making it impossible to reset the conversation after one inquiry. If an API timeout occurred, the UI could retain an orphaned user message without an assistant response or recovery path.
  3. In `app/components/cv_review.py`, switching target jobs did not clear `cv_suggestions`, remaining stuck on the first job's analysis.
- **Fix** (2026-09-19):
  1. Stored full chunk text in `metadata.pkl` across all 53 indexed chunks and rebuilt the index.
  2. Added a "🗑️ Clear Chat" button in the Career Mentor header to start fresh conversations anytime.
  3. Wrapped answer generation in error boundaries with user feedback.
  4. Updated CV Studio to automatically reset suggestions when selecting a different target job.
  5. **All 25/25 pytest tests now pass (100%)**.
