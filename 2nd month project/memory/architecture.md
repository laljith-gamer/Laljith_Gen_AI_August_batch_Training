# SmartHire GenAI - System Architecture

## Overview
SmartHire GenAI is an end-to-end career intelligence portal designed to provide resume parsing with Human-in-the-Loop (HITL) approval, semantic job matching using FAISS vector search, AI-driven CV improvement recommendations, and a grounded AI Career Mentor chatbot using Retrieval-Augmented Generation (RAG).

## High-Level Architecture Flow
```text
Resume Upload (PDF/DOCX)
        │
        ▼
Document Loader & Normalization
        │
        ▼
Gemini 3.8 Flash Structured Parser (Pydantic Schema)
        │
        ▼
   ┌────────────────────────────────┐
   │ HUMAN-IN-THE-LOOP REVIEW       │
   │ State: REQUIRES_REVIEW         │
   │ Actions: Approve / Edit / Reset│
   └───────────────┬────────────────┘
                   │
                   ▼
         Approved Candidate Profile
         (Status: APPROVED)
                   │
         ┌─────────┴────────────────────────┐
         │                                  │
         ▼                                  ▼
Profile Embedding                  Target Job Selection
(gemini-embedding-001)                      │
         │                                  ▼
         ▼                          CV Improvement Engine
FAISS Job Search                     (Gemini 3.8 Flash)
         │                                  │
         ▼                                  ▼
Top-N Semantic Job Matches         ┌───────────────────────────────┐
         │                         │ HUMAN-IN-THE-LOOP CV REVIEW   │
         ▼                         │ Actions: Accept / Edit /      │
Display & Relevance Feedback       │          Reject / Regenerate  │
                                   └───────────────┬───────────────┘
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
                                        User Feedback (Helpful / Unhelpful)
```

## Subsystems
1. **Resume Parser**: Multi-format document loading (`pypdf`, `python-docx`), text cleaning, Pydantic structured output validation with `gemini-3.8-flash`.
2. **HITL Profile Review**: Explicit state machine preventing unapproved data propagation. User can edit any extracted field, compare against AI output, and approve.
3. **Embeddings & Vector Store**: `gemini-embedding-001` (3072 dims) with caching layer and local TF-IDF cosine fallback; persistent FAISS index for jobs and career notes.
4. **Semantic Job Search**: Queries job index with approved profile, computes semantic similarity scores, extracts matched and missing skills.
5. **CV Improvement Studio**: Targets selected job with structured prompt library to identify missing skills, weak bullet points, rewrite summary and bullets, strictly without hallucinating candidate qualifications.
6. **AI Career Mentor**: RAG chatbot grounded strictly on knowledge base documents (career roadmaps, guides, job postings). Responds "I don't know based on the available documents" when unsupported.
7. **Guardrails & Security**: Pre-generation guardrails against prompt injection, credential exfiltration, fake credentials, and off-topic requests.
8. **Evaluation Suite**: Automated tests for retrieval hit rate, answer grounding, prompt comparison, hallucination refusal, and HITL metrics.
9. **Streamlit UI**: Full-featured interactive dashboard with persistent session state, feedback logging, and workflow control.
