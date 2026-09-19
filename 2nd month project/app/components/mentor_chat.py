"""
Interactive AI Career Mentor Chat Component powered by Grounded RAG and Guardrails.
Calm, natural career coaching grounded strictly in verified roadmaps and interview frameworks.
"""

import logging
from typing import List, Dict, Any
import streamlit as st

from src.models.schemas import MentorResponse
from src.mentor.rag_chain import MentorRAGChain
from src.human_loop.feedback import FeedbackManager
from src.human_loop.audit import AuditLogger
from app.state import AppStateManager

logger = logging.getLogger(__name__)

def render_mentor_chat():
    head_col1, head_col2 = st.columns([4, 1])
    with head_col1:
        st.subheader("Career mentor")
        st.markdown(
            "Ask about interview preparation frameworks, skill transitions, or career roadmaps. "
            "Answers are **strictly grounded in verified career guides** with traceable citations."
        )
    with head_col2:
        st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
        if st.button("New conversation", help="Start a fresh conversation"):
            st.session_state.mentor_chat_history = []
            st.session_state.pop("pending_mentor_query", None)
            st.rerun()

    # Pre-canned conversation starters (natural questions)
    st.caption("Suggested conversation starters:")
    q1, q2, q3 = st.columns(3)
    preset_query = None
    with q1:
        if st.button("Preparing for behavioral interviews (STAR)"):
            preset_query = "Explain how to prepare for interviews using the STAR method."
    with q2:
        if st.button("Transitioning from Backend to AI/ML"):
            preset_query = "How can a Backend Developer transition into Machine Learning and GenAI?"
    with q3:
        if st.button("Skills required for Data Analytics"):
            preset_query = "What skills and tools are required for a Data Analyst role?"

    if preset_query:
        st.session_state.pending_mentor_query = preset_query

    # Chat history container
    if "mentor_chat_history" not in st.session_state:
        st.session_state.mentor_chat_history = []

    chat_history: List[Dict[str, Any]] = st.session_state.mentor_chat_history

    if not chat_history and not st.session_state.get("pending_mentor_query"):
        with st.container(border=True):
            st.markdown("**Welcome to your Career Mentor**")
            st.caption(
                "You can ask any technical career question below. For example: "
                "'How should I structure resume bullets?', 'What should I study for a system design interview?', "
                "or click one of the suggested topics above."
            )

    for idx, msg in enumerate(chat_history):
        role = msg.get("role", "user")
        with st.chat_message(role):
            st.markdown(msg.get("content", ""))
            if role == "assistant" and msg.get("citations"):
                with st.expander(f"Sources ({len(msg['citations'])} documents)", expanded=False):
                    for c in msg["citations"]:
                        st.markdown(f"• **{c.get('source_title', 'Document')}** (Chunk {c.get('chunk_index', 0)})")
                        if c.get("snippet"):
                            st.caption(f"Excerpt: *\"{c['snippet']}...\"*")

                # Subtle feedback buttons
                f_col1, f_col2, f_col3 = st.columns([1, 1, 5])
                with f_col1:
                    if st.button("Helpful", key=f"f_help_{idx}"):
                        sources = [c.get("source_title", "") for c in msg.get("citations", [])]
                        FeedbackManager.record_mentor_feedback(msg.get("question", ""), msg.get("content", ""), "helpful", sources)
                        st.toast("Thank you for your feedback.")
                with f_col2:
                    if st.button("Not helpful", key=f"f_unhelp_{idx}"):
                        sources = [c.get("source_title", "") for c in msg.get("citations", [])]
                        FeedbackManager.record_mentor_feedback(msg.get("question", ""), msg.get("content", ""), "not_helpful", sources)
                        st.toast("Feedback recorded.")

    # User Input handling
    user_input = st.chat_input("Ask your career mentor a question...")
    query_to_process = st.session_state.pop("pending_mentor_query", None) or user_input

    if query_to_process:
        # Append user message
        st.session_state.mentor_chat_history.append({"role": "user", "content": query_to_process})
        with st.chat_message("user"):
            st.markdown(query_to_process)

        # Generate response with error boundary
        with st.chat_message("assistant"):
            with st.spinner("Checking career knowledge base..."):
                try:
                    rag_chain = MentorRAGChain(api_key=AppStateManager.get_api_key())
                    response: MentorResponse = rag_chain.answer_question(query_to_process)
                except Exception as exc:
                    logger.error(f"Mentor query failed: {exc}", exc_info=True)
                    response = MentorResponse(
                        question=query_to_process,
                        answer="The mentor is temporarily unavailable. Please check your network connection and try again.",
                        citations=[],
                        is_grounded=False,
                        refusal=True,
                    )

                st.markdown(response.answer)

                if response.citations:
                    with st.expander(f"Sources ({len(response.citations)} documents)", expanded=False):
                        for c in response.citations:
                            st.markdown(f"• **{c.source_title}**")
                            if c.snippet:
                                st.caption(f"Excerpt: *\"{c.snippet}...\"*")

                citations_dict = [c.model_dump() for c in response.citations]
                st.session_state.mentor_chat_history.append({
                    "role": "assistant",
                    "content": response.answer,
                    "question": query_to_process,
                    "citations": citations_dict,
                })

                AuditLogger.log_event("MENTOR_QUERY_ANSWERED", "AI", "SUCCESS", {
                    "question": query_to_process,
                    "is_grounded": response.is_grounded,
                    "refusal": response.refusal,
                    "citations_count": len(response.citations),
                })
                st.rerun()
