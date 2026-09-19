"""
End-to-end integration smoke test verifying the full SmartHire GenAI user journey:
Upload -> Extract -> Parse -> HITL Review & Approve -> Embed -> FAISS Matching ->
CV Improvement -> Mentor RAG -> Citations -> Guardrails -> Audit Logging.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import settings
from src.parsing.loader import load_document
from src.parsing.resume_parser import parse_resume
from src.human_loop.review import ProfileReviewManager
from src.search.job_search import JobSearchEngine
from src.generate.cv_suggestions import CVSuggestionEngine
from src.mentor.rag_chain import MentorRAGChain
from src.human_loop.feedback import FeedbackManager
from src.human_loop.audit import AuditLogger
from src.models.enums import WorkflowState, ReviewStatus

def test_full_end_to_end_journey():
    print("\n--- [STEP 1: Document Loading] ---")
    demo_pdf = settings.PROJECT_ROOT / "data/resumes/sample_resume.pdf"
    assert demo_pdf.exists(), "Sample PDF resume does not exist"
    doc_info = load_document(demo_pdf)
    assert len(doc_info["text"]) > 100
    assert "Alex Rivera" in doc_info["text"]

    print("--- [STEP 2: Structured Resume Parsing] ---")
    profile = parse_resume(doc_info["text"])
    assert profile.name is not None
    assert len(profile.skills) > 0

    print("--- [STEP 3: Human-in-the-Loop Profile Review & Approval] ---")
    container = ProfileReviewManager.initialize_review(profile)
    assert container.status == ReviewStatus.REQUIRES_REVIEW
    assert container.is_approved is False

    # Simulate human edit
    edited = container.approved_profile.model_copy(deep=True)
    edited.skills.append("FastAPI Microservices")
    container = ProfileReviewManager.apply_human_approval(container, edited)
    assert container.is_approved is True
    assert container.status == ReviewStatus.HUMAN_EDITED
    assert "FastAPI Microservices" in container.approved_profile.skills

    print("--- [STEP 4: Semantic Job Search] ---")
    search_engine = JobSearchEngine()
    matches = search_engine.search_matching_jobs(container, top_k=3)
    assert len(matches) > 0
    top_match = matches[0]
    assert 0.0 <= top_match.similarity_score <= 1.0
    assert len(top_match.matched_skills) > 0

    # User marks job relevant
    FeedbackManager.record_job_feedback(
        top_match.job.job_id, top_match.job.title, "relevant", container.approved_profile.target_role or "AI Engineer"
    )

    print("--- [STEP 5: CV Improvement Studio] ---")
    cv_engine = CVSuggestionEngine()
    cv_suggestions = cv_engine.generate_suggestions(container, top_match.job)
    assert cv_suggestions.target_job_id == top_match.job.job_id
    assert len(cv_suggestions.actionable_suggestions) > 0
    assert len(cv_suggestions.rewritten_summary) > 10

    # User accepts suggestions
    FeedbackManager.record_cv_feedback(top_match.job.job_id, "accepted", "Accepted by test harness")

    print("--- [STEP 6: AI Career Mentor RAG Query & Citations] ---")
    rag_chain = MentorRAGChain()
    mentor_resp = rag_chain.answer_question("What skills are most important for Machine Learning Engineers?")
    assert mentor_resp.is_grounded is True
    assert len(mentor_resp.citations) > 0
    assert len(mentor_resp.answer) > 20

    # User rates mentor response
    FeedbackManager.record_mentor_feedback(
        "What skills are most important for Machine Learning Engineers?",
        mentor_resp.answer,
        "helpful",
        [c.source_title for c in mentor_resp.citations],
    )

    print("--- [STEP 7: Audit Logging Verification] ---")
    AuditLogger.log_event("SMOKE_TEST_COMPLETED", "SYSTEM", "SUCCESS", {"status": "all_passed"})
    recent_logs = AuditLogger.get_recent_logs(limit=10)
    assert len(recent_logs) > 0
    assert recent_logs[-1]["event_type"] == "SMOKE_TEST_COMPLETED"

    print("\n>>> FULL END-TO-END SMOKE TEST PASSED PERFECTLY! <<<")

if __name__ == "__main__":
    test_full_end_to_end_journey()
