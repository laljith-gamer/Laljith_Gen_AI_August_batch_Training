# SmartHire GenAI - Answer Quality & Evaluation Report

**Generated:** 2026-09-30T18:16:26.405292

## 1. Retrieval Relevance Benchmark
- **Total Test Queries:** 5
- **Hits (Relevant Top-3):** 5
- **Retrieval Hit Rate:** 100.0%

### Retrieval Query Breakdown
| Target Role | Retrieved Titles | Hit |
| :--- | :--- | :--- |
| Data Analyst | Analytics Engineer Openings Based out in Bangalore, Lead Data Engineer - Commercial Analytics | Yes |
| Machine Learning Engineer | Analytics Engineer Openings Based out in Bangalore, Machine Learning & NLP Expert -candidates From Premier Institutes Only | Yes |
| Senior Backend Developer | Sr.java Developer(server side JAVA Programming), Sr.java Developer | Yes |
| Cybersecurity Analyst | DPI Sr. System Analyst Position with a Telecom Product Based org., Information Security Engineer - Contract to Hire - Bangalore | Yes |
| Analytics Engineer | Analytics Engineer Openings Based out in Bangalore, Lead Data Engineer - Commercial Analytics | Yes |

---

## 2. Hallucination Refusal Benchmark
- **Total Intentionally Unsupported Questions:** 3
- **Correct Refusals:** 3
- **Refusal Accuracy:** 100.0%

> [!NOTE]
> System appropriately refuses queries when grounding evidence is absent, adhering to: *"I don't know based on the available documents."*

---

## 3. Prompt Comparison Analysis
- **Query Tested:** "How should I structure bullet points on my resume?"
- **Naive Prompt Behavior:** Generic advice without document traceability, prone to fabricating metrics.
- **Grounded Prompt Behavior:** Restricted strictly to the XYZ formula from resume_writing_guide.txt with traceable citations.
- **Citations Generated:** Resume Writing Guide, Data Analyst Roadmap, Resume Writing Guide

---

## 4. Human-in-the-Loop Feedback Telemetry
- **Total Job Feedback:** 73 (Relevance Rate: 100.0%)
- **Total Mentor Feedback:** 73 (Helpfulness Rate: 100.0%)
- **CV Suggestions Actions:** 36 (Accepted: 36, Edited: 0, Rejected: 0)

---

## 5. Dataset Information
- **Dataset Mode:** raw_kaggle
- **Dataset Source:** Kaggle Naukri Production Corpus (PromptCloudHQ/jobs-on-naukricom)
- **Prepared Jobs in Corpus:** 21,739
- **Jobs Indexed in FAISS:** 500
- **Index Status:** Partial Development Subset (500 / 21,739 indexed)
- **Dataset Path:** data/jobs/jobs_kaggle_naukri.csv
