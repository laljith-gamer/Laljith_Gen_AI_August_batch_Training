# SmartHire GenAI — Capstone Final Project Report

**Project Title:** SmartHire GenAI — Resume Matching & AI Career Mentor  
**Technologies:** Google Gemini 3.8/3.6 Flash, Text Embeddings, FAISS Vector Database, LangChain RAG, Pydantic, Streamlit  
**Date:** September 2026  

---

## 1. Executive Summary

SmartHire GenAI is an intelligent career portal that bridges the gap between candidate resumes and modern employment opportunities. Unlike traditional keyword-matching Applicant Tracking Systems (ATS), SmartHire uses generative AI, vector embeddings, and Retrieval-Augmented Generation (RAG) to provide:
1. **Automated Structured Resume Extraction** into typed, validated schemas with Human-in-the-Loop review.
2. **Semantic Job Matching** using cosine similarity over a pre-indexed vector corpus in FAISS.
3. **Targeted CV Improvement Suggestions** targeting missing skills, weak bullet points, and rewritten summaries.
4. **AI Career Mentor Chatbot** grounded strictly in verified career notes, role roadmaps, and interview standards with zero tolerance for hallucinations.
5. **Kaggle 24-Industry Resume Explorer & Dynamic JSON Generator** capable of parsing thousands of diverse resumes on demand.

---

## 2. Design Choices & Architecture

### A. LLM & Embedding Selection
- **Primary LLM:** `gemini-3.8-flash` (with automated fallback to `gemini-3.6-flash` for high throughput and rate-limit resilience).
- **Embedding Engine:** `gemini-embedding-001` (3072-dimensional normalized vectors) coupled with an in-memory normalized fallback hash vectorizer ensuring offline/test reliability.
- **Structured Outputs:** Leveraging Gemini's native `response_json_schema` backed by Pydantic models (`ResumeProfile`, `DynamicResumeJSON`) to enforce clean, predictable data contracts.

### B. Vector Storage & Retrieval
- **Engine:** Facebook AI Similarity Search (`faiss-cpu`) using `IndexFlatIP` on L2-normalized vectors (mathematically equivalent to cosine similarity).
- **Dual Vector Spaces:**
  1. **Job Index (`vectorstore/jobs/`):** Indexes titles, skills, and full descriptions of industry roles.
  2. **Mentor Index (`vectorstore/mentor/`):** Indexes chunked career guides, roadmaps, and interview prep notes.

### C. Human-in-the-Loop (HITL) State Machine
- Strict architectural guardrail: candidates must review and approve their extracted profile before downstream semantic matching or CV suggestions execute.
- Prevents cascading hallucinations from unverified LLM parser extractions.

### D. Grounded RAG & Responsible AI Guardrails
- **Lexical & Semantic Grounding:** Mentor answers are conditioned exclusively on retrieved chunks.
- **Strict Out-of-Scope Refusal:** When asked questions outside career guidance (or unsupported facts), the mentor enforces: *"I don't know based on the available documents."*
- **Safety Guardrails:** Pre-execution regex and semantic filters intercept prompt injections, secret exfiltration, and fraudulent resume tailoring attempts.

---

## 3. What Worked Well

1. **Semantic Search Superiority:** Candidate profiles match roles based on conceptual skill overlap (e.g. PyTorch matching Deep Learning positions) rather than literal token matches.
2. **Deterministic Fallbacks:** The multi-tiered architecture (Gemini 3.8 → Gemini 3.6 → Heuristic Parser) achieved a 100% test suite pass rate (30/30 unit & integration tests) even under API quotas.
3. **Calm SaaS User Experience:** Converting fragmented tab interfaces into a sequential 5-step workspace with native Light/Dark themes created a serious, presentation-ready product.
4. **Dynamic JSON Generation:** Processing resumes dynamically from Kaggle's 2,484-resume dataset unlocks instant multi-industry demonstrations without storage overhead.

---

## 4. Limitations & Future Roadmap

1. **Static Job Corpus:** The current job catalog is pre-collected from Kaggle rather than live web scraping (complying with platform Terms of Service). Future iterations could integrate official LinkedIn or Indeed APIs.
2. **Multi-Page Resume Complexity:** Highly non-standard multi-column resume PDFs occasionally require human adjustments during the HITL review step.
3. **Cross-Encoder Re-ranking:** While bi-encoder FAISS retrieval achieves high recall, adding a cross-encoder re-ranking stage (e.g., FlashRank or BGE-Reranker) could further refine top-3 ranking precision.
