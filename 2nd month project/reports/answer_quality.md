# SmartHire GenAI - Answer Quality & Evaluation Report

**Generated:** 2026-09-19T12:04:38.966792

## 1. Retrieval Relevance Benchmark
- **Total Test Queries:** 5
- **Hits (Relevant Top-3):** 5
- **Retrieval Hit Rate:** 100.0%

### Retrieval Query Breakdown
| Target Role | Retrieved Titles | Hit |
| :--- | :--- | :--- |
| Data Analyst | Data Analyst, Analytics Engineer | ✅ Yes |
| Machine Learning Engineer | Machine Learning Engineer, Analytics Engineer | ✅ Yes |
| Senior Backend Developer | Senior Backend Developer, Senior Generative AI Engineer | ✅ Yes |
| Cybersecurity Analyst | Cybersecurity Incident Analyst, Site Reliability Engineer (SRE) | ✅ Yes |
| Analytics Engineer | Analytics Engineer, Data Platform Engineer | ✅ Yes |

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
- **Citations Generated:** Resume Writing Guide, Data Analyst Roadmap, Resume Writing Guide, Resume Writing Guide

---

## 4. Human-in-the-Loop Feedback Telemetry
- **Total Job Feedback:** 16 (Relevance Rate: 100.0%)
- **Total Mentor Feedback:** 17 (Helpfulness Rate: 100.0%)
- **CV Suggestions Actions:** 7 (Accepted: 7, Edited: 0, Rejected: 0)
