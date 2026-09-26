"""
Interactive AI Career Mentor Chat Component inspired by modern ChatGPT canvas.
Features:
- Minimalist hero: "What's on the agenda today?" with zero canned prompt clutter
- Deep reasoning toggle: "Think" with Streamlit compact status ("Thought for N seconds")
- ChatGPT-style SQL Database History (Today, Previous 7 Days, Older) with + New Chat
- ChatGPT-style Candidate Memory (persisted in SQL database and automatically populated from resume)
- Automatic resume data extraction + native file attachment in chat input
- Backed by persistent SQL database (configured via Streamlit Secrets / st.secrets)
"""

import time
import datetime
import logging
from typing import List, Dict, Any, Optional
import streamlit as st

from src.models.schemas import MentorResponse
from src.mentor.rag_chain import MentorRAGChain
from src.mentor.candidate_context import CandidateContextManager
from src.human_loop.feedback import FeedbackManager
from src.human_loop.audit import AuditLogger
from src.human_loop.review import ProfileReviewManager
from src.parsing.loader import load_document
from src.parsing.resume_parser import parse_resume
from src.models.enums import WorkflowState
from app.state import AppStateManager
from app.ui import render_badge
from app.components.mentor_storage import MentorDatabaseManager
from app.components.mentor_memory import MentorMemoryManager

logger = logging.getLogger(__name__)


def _group_sessions_by_date(sessions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group saved sessions into ChatGPT-style buckets: Today, Yesterday, Previous 7 days, Older."""
    now = datetime.datetime.now(datetime.timezone.utc)
    today_date = now.date()
    yesterday_date = today_date - datetime.timedelta(days=1)
    seven_days_ago = today_date - datetime.timedelta(days=7)

    groups: Dict[str, List[Dict[str, Any]]] = {
        "Today": [],
        "Yesterday": [],
        "Previous 7 days": [],
        "Older": [],
    }

    for s in sessions:
        up_str = s.get("updated_at")
        if not up_str:
            groups["Older"].append(s)
            continue
        try:
            dt = datetime.datetime.fromisoformat(up_str.replace("Z", "+00:00"))
            s_date = dt.date()
            if s_date == today_date:
                groups["Today"].append(s)
            elif s_date == yesterday_date:
                groups["Yesterday"].append(s)
            elif s_date >= seven_days_ago:
                groups["Previous 7 days"].append(s)
            else:
                groups["Older"].append(s)
        except Exception:
            groups["Older"].append(s)

    return groups


def render_mentor_chat():
    """Render the ChatGPT-inspired Career Mentor canvas."""

    # 1. State initialization
    if "mentor_session_id" not in st.session_state:
        st.session_state.mentor_session_id = f"session_{int(time.time() * 1000)}"

    if "mentor_chat_history" not in st.session_state:
        # Load existing messages for active session from database if available
        loaded = MentorDatabaseManager.load_session(st.session_state.mentor_session_id)
        st.session_state.mentor_chat_history = loaded

    if "mentor_think_mode" not in st.session_state:
        st.session_state.mentor_think_mode = False

    # Extract candidate context automatically from uploaded resume
    candidate_ctx = CandidateContextManager.extract_from_session_state(st.session_state)
    has_resume = candidate_ctx.get("has_resume", False)
    cand_name = candidate_ctx.get("name", "Candidate")
    cand_role = candidate_ctx.get("target_role", "Engineering / Tech")

    # Initialize ChatGPT-style candidate memories from database or context
    MentorMemoryManager.initialize_memories(candidate_ctx)
    memories = MentorMemoryManager.get_memories()

    # 2. Fetch saved sessions from database
    saved_sessions = MentorDatabaseManager.list_sessions()

    # 3. Top Action Toolbar (History + New Chat + Think + Memory + DB Status)
    col_hist, col_new, col_think, col_mem = st.columns([1.2, 1, 1, 1.2])

    with col_new:
        if st.button("＋ New chat", key="btn_mentor_new_chat", type="secondary", width="stretch", help="Start a fresh conversation"):
            new_id = f"session_{int(time.time() * 1000)}"
            st.session_state.mentor_chat_history = []
            st.session_state.mentor_session_id = new_id
            st.toast("Started fresh conversation.")
            st.rerun()

    with col_think:
        think_active = st.session_state.get("mentor_think_mode", False)
        think_type = "primary" if think_active else "secondary"
        if st.button(":material/psychology: Think", key="btn_mentor_think_toggle", type=think_type, width="stretch", help="Toggle deep reasoning mode"):
            st.session_state.mentor_think_mode = not think_active
            st.toast(f"Deep reasoning mode: {'ON' if not think_active else 'OFF'}")
            st.rerun()

    with col_hist:
        # History Popover (Grouped by Today, Yesterday, Previous 7 days, Older)
        hist_label = f":material/history: History ({len(saved_sessions)})" if saved_sessions else ":material/history: History"
        with st.popover(hist_label, width="stretch", help="Browse and restore saved chat history from database"):
            # Inject Scoped CSS for Chat History Popover
            st.markdown(
                """
                <style>
                /* Chat History Header */
                .mentor-hist-header {
                    display: flex;
                    flex-direction: column;
                    gap: 1px;
                    margin: 0 0 2px 0;
                    padding: 0;
                }
                .mentor-hist-title {
                    font-size: 1.15rem !important;
                    font-weight: 600 !important;
                    color: #f8fafc !important;
                    letter-spacing: -0.01em !important;
                    line-height: 1.25 !important;
                }
                .mentor-hist-subtitle {
                    font-size: 0.8rem !important;
                    color: #94a3b8 !important;
                    line-height: 1.2 !important;
                }

                /* Close Ghost Button (Top-Right) */
                div[class*="st-key-btn_close_history_popover"] {
                    display: flex !important;
                    justify-content: flex-end !important;
                    align-items: center !important;
                }
                div[class*="st-key-btn_close_history_popover"] button {
                    background: transparent !important;
                    border: none !important;
                    color: #64748b !important;
                    height: 28px !important;
                    width: 28px !important;
                    min-width: 28px !important;
                    padding: 0 !important;
                    border-radius: 6px !important;
                    box-shadow: none !important;
                    transition: all 0.15s ease !important;
                    display: flex !important;
                    align-items: center !important;
                    justify-content: center !important;
                }
                div[class*="st-key-btn_close_history_popover"] button:hover {
                    background: rgba(255, 255, 255, 0.08) !important;
                    color: #e2e8f0 !important;
                }

                /* Compact Export Action */
                div[class*="st-key-btn_export_active_chat"] {
                    margin: 6px 0 8px 0 !important;
                }
                div[class*="st-key-btn_export_active_chat"] button {
                    background: rgba(255, 255, 255, 0.035) !important;
                    border: 1px solid rgba(255, 255, 255, 0.08) !important;
                    color: #cbd5e1 !important;
                    font-size: 0.8rem !important;
                    font-weight: 500 !important;
                    height: 34px !important;
                    min-height: 34px !important;
                    padding: 0 12px !important;
                    border-radius: 8px !important;
                    box-shadow: none !important;
                    transition: all 0.15s ease !important;
                    display: inline-flex !important;
                    align-items: center !important;
                    gap: 6px !important;
                    width: auto !important;
                }
                div[class*="st-key-btn_export_active_chat"] button:hover {
                    background: rgba(255, 255, 255, 0.07) !important;
                    border-color: rgba(59, 130, 246, 0.35) !important;
                    color: #ffffff !important;
                }
                div[class*="st-key-btn_export_active_chat"] button svg {
                    width: 14px !important;
                    height: 14px !important;
                }

                /* Date Grouping Labels */
                .mentor-hist-date-label {
                    font-size: 0.72rem !important;
                    font-weight: 600 !important;
                    text-transform: uppercase !important;
                    letter-spacing: 0.06em !important;
                    color: #94a3b8 !important;
                    margin: 10px 0 4px 4px !important;
                    user-select: none !important;
                }

                /* Scrollable List Area */
                div[class*="st-key-mentor_history_scroll"] {
                    max-height: 44vh !important;
                    overflow-y: auto !important;
                    overflow-x: hidden !important;
                    padding-right: 2px !important;
                    margin: 4px 0 !important;
                    scrollbar-width: thin !important;
                    scrollbar-color: rgba(255, 255, 255, 0.12) transparent !important;
                }
                div[class*="st-key-mentor_history_scroll"]::-webkit-scrollbar {
                    width: 4px !important;
                }
                div[class*="st-key-mentor_history_scroll"]::-webkit-scrollbar-thumb {
                    background: rgba(255, 255, 255, 0.12) !important;
                    border-radius: 4px !important;
                }

                /* Conversation Row / Card */
                div[class*="st-key-mentor_history_scroll"] div[data-testid="stHorizontalBlock"] {
                    background: rgba(255, 255, 255, 0.025) !important;
                    border: 1px solid rgba(255, 255, 255, 0.06) !important;
                    border-radius: 10px !important;
                    padding: 2px 4px 2px 8px !important;
                    margin-bottom: 6px !important;
                    align-items: center !important;
                    transition: all 0.15s ease !important;
                }
                div[class*="st-key-mentor_history_scroll"] div[data-testid="stHorizontalBlock"]:hover {
                    background: rgba(255, 255, 255, 0.055) !important;
                    border-color: rgba(255, 255, 255, 0.12) !important;
                }

                /* Active Selected Conversation (Subtle blue accent, never saturated red) */
                div[class*="st-key-mentor_history_scroll"] div[data-testid="stHorizontalBlock"]:has(button[kind="primary"]) {
                    background: rgba(59, 130, 246, 0.09) !important;
                    border: 1px solid rgba(59, 130, 246, 0.35) !important;
                }
                div[class*="st-key-mentor_history_scroll"] div[data-testid="stHorizontalBlock"]:has(button[kind="primary"]):hover {
                    background: rgba(59, 130, 246, 0.15) !important;
                    border-color: rgba(59, 130, 246, 0.48) !important;
                }

                /* Conversation Title Button */
                div[class*="st-key-hist_load_"] button {
                    background: transparent !important;
                    border: none !important;
                    padding: 0 4px !important;
                    height: 38px !important;
                    min-height: 38px !important;
                    text-align: left !important;
                    justify-content: flex-start !important;
                    box-shadow: none !important;
                    width: 100% !important;
                }
                div[class*="st-key-hist_load_"] button p {
                    text-align: left !important;
                    overflow: hidden !important;
                    text-overflow: ellipsis !important;
                    white-space: nowrap !important;
                    color: #e2e8f0 !important;
                    font-size: 0.86rem !important;
                    font-weight: 450 !important;
                    margin: 0 !important;
                }
                div[class*="st-key-hist_load_"] button[kind="primary"] p {
                    color: #93c5fd !important;
                    font-weight: 500 !important;
                }

                /* Direct button fallback for kind="primary" */
                div[class*="st-key-hist_load_"] button[kind="primary"] {
                    background: rgba(59, 130, 246, 0.12) !important;
                    border: 1px solid rgba(59, 130, 246, 0.35) !important;
                    color: #93c5fd !important;
                    border-radius: 10px !important;
                }
                div[class*="st-key-hist_load_"] button[kind="primary"]:hover {
                    background: rgba(59, 130, 246, 0.2) !important;
                    border-color: rgba(59, 130, 246, 0.5) !important;
                }

                /* Delete Trash Button */
                div[class*="st-key-hist_del_"] button {
                    background: transparent !important;
                    border: none !important;
                    color: #64748b !important;
                    height: 34px !important;
                    width: 34px !important;
                    min-width: 34px !important;
                    padding: 0 !important;
                    border-radius: 8px !important;
                    display: flex !important;
                    align-items: center !important;
                    justify-content: center !important;
                    box-shadow: none !important;
                    transition: all 0.15s ease !important;
                }
                div[class*="st-key-hist_del_"] button:hover {
                    background: rgba(248, 113, 113, 0.14) !important;
                    color: #f87171 !important;
                }
                div[class*="st-key-hist_del_"] button span,
                div[class*="st-key-hist_del_"] button svg {
                    font-size: 1rem !important;
                    color: inherit !important;
                }

                /* Clear History Action */
                .mentor-hist-divider {
                    border-top: 1px solid rgba(255, 255, 255, 0.07);
                    margin: 8px 0 4px 0;
                }
                div[class*="st-key-btn_clear_all_chats"] button {
                    background: transparent !important;
                    border: none !important;
                    color: #94a3b8 !important;
                    font-size: 0.8rem !important;
                    font-weight: 500 !important;
                    height: 30px !important;
                    min-height: 30px !important;
                    padding: 0 !important;
                    border-radius: 6px !important;
                    box-shadow: none !important;
                    display: flex !important;
                    align-items: center !important;
                    justify-content: center !important;
                    transition: all 0.15s ease !important;
                }
                div[class*="st-key-btn_clear_all_chats"] button:hover {
                    background: rgba(248, 113, 113, 0.08) !important;
                    color: #f87171 !important;
                }

                /* Empty state */
                .mentor-hist-empty {
                    padding: 24px 12px;
                    text-align: center;
                    display: flex;
                    flex-direction: column;
                    gap: 4px;
                }
                .mentor-hist-empty-title {
                    color: #cbd5e1;
                    font-size: 0.86rem;
                    font-weight: 500;
                }
                .mentor-hist-empty-desc {
                    color: #64748b;
                    font-size: 0.76rem;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )

            # Compact Header: Chat History + Your conversations on Left, Close on Right
            col_head_text, col_head_close = st.columns([5.2, 0.8], vertical_alignment="center")
            with col_head_text:
                st.markdown(
                    """
                    <div class="mentor-hist-header">
                        <div class="mentor-hist-title">Chat History</div>
                        <div class="mentor-hist-subtitle">Your conversations</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col_head_close:
                if st.button(":material/close:", key="btn_close_history_popover", help="Close history"):
                    st.rerun()

            # Compact Export Action directly below Header
            if st.session_state.mentor_chat_history:
                export_json = MentorDatabaseManager.export_session_json(st.session_state.mentor_session_id)
                st.download_button(
                    ":material/download: Export JSON",
                    data=export_json,
                    file_name=f"mentor_chat_{st.session_state.mentor_session_id}.json",
                    mime="application/json",
                    key="btn_export_active_chat",
                    help="Export current conversation as JSON",
                )

            # Scrollable History List
            if not saved_sessions:
                st.markdown(
                    """
                    <div class="mentor-hist-empty">
                        <span class="mentor-hist-empty-title">No conversations yet</span>
                        <span class="mentor-hist-empty-desc">Your chat history will be automatically saved here.</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                grouped = _group_sessions_by_date(saved_sessions)
                with st.container(key="mentor_history_scroll"):
                    for group_name, sess_list in grouped.items():
                        if sess_list:
                            st.markdown(f'<div class="mentor-hist-date-label">{group_name}</div>', unsafe_allow_html=True)
                            for s in sess_list:
                                s_id = s.get("id")
                                s_title = s.get("title") or "Career Discussion"
                                short_title = (s_title[:28] + "...") if len(s_title) > 28 else s_title
                                is_curr = s_id == st.session_state.mentor_session_id

                                row_col1, row_col2 = st.columns([5.3, 0.9], gap="small", vertical_alignment="center")
                                with row_col1:
                                    btn_type = "primary" if is_curr else "secondary"
                                    if st.button(
                                        short_title,
                                        key=f"hist_load_{s_id}",
                                        type=btn_type,
                                        help=f"{s_title}\n({s.get('message_count', 0)} messages)",
                                        width="stretch",
                                    ):
                                        msgs = MentorDatabaseManager.load_session(s_id)
                                        st.session_state.mentor_session_id = s_id
                                        st.session_state.mentor_chat_history = msgs
                                        st.toast(f"Loaded: '{short_title}'")
                                        st.rerun()
                                with row_col2:
                                    if st.button(":material/delete:", key=f"hist_del_{s_id}", help="Delete this chat from database"):
                                        MentorDatabaseManager.delete_session(s_id)
                                        if s_id == st.session_state.mentor_session_id:
                                            st.session_state.mentor_chat_history = []
                                            st.session_state.mentor_session_id = f"session_{int(time.time() * 1000)}"
                                        st.toast("Conversation deleted.")
                                        st.rerun()

                # Bottom Pinned Clear Action
                st.markdown('<div class="mentor-hist-divider"></div>', unsafe_allow_html=True)
                if st.button("Clear all chat history", key="btn_clear_all_chats", type="secondary", width="stretch", help="Permanently clear all saved conversations"):
                    MentorDatabaseManager.clear_all_sessions()
                    st.session_state.mentor_chat_history = []
                    st.session_state.mentor_session_id = f"session_{int(time.time() * 1000)}"
                    st.toast("Database chat history cleared.")
                    st.rerun()

    with col_mem:
        # Memory Popover (ChatGPT-style Memory)
        active_mems = MentorMemoryManager.get_memories()
        mem_count_label = f":material/psychology: Memory ({len(active_mems)})" if active_mems else ":material/psychology: Memory"
        with st.popover(mem_count_label, width="stretch", help="Manage persistent candidate facts remembered across chats"):
            st.markdown("##### Candidate Memory")
            st.caption("Facts stored in database to personalize career guidance across sessions.")

            if not active_mems:
                st.info("No active memories recorded. Attach a resume via chat (+) to save facts automatically.")
            else:
                for idx, mem in enumerate(active_mems):
                    m_c1, m_c2 = st.columns([5, 1])
                    with m_c1:
                        st.markdown(f"• {mem}")
                    with m_c2:
                        if st.button(":material/close:", key=f"del_mem_{idx}", help="Forget this memory fact"):
                            MentorMemoryManager.remove_memory(idx)
                            st.toast("Memory removed.")
                            st.rerun()

            st.divider()
            new_mem_input = st.text_input(
                "Add custom memory note:",
                placeholder="e.g., Prefers remote roles, aiming for $220k+",
                key="input_new_memory_fact",
            )
            if st.button("Save to Memory", key="btn_save_custom_mem", width="stretch") and new_mem_input:
                MentorMemoryManager.add_memory(new_mem_input)
                st.toast("Memory saved to database.")
                st.rerun()

            if active_mems:
                st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
                if st.button("Clear all memories", key="btn_clear_all_memories", type="secondary", width="stretch"):
                    MentorMemoryManager.clear_memories()
                    st.toast("Candidate memories cleared from database.")
                    st.rerun()

    # 4. Minimalist ChatGPT Hero (When conversation is empty)
    chat_history: List[Dict[str, Any]] = st.session_state.mentor_chat_history

    if not chat_history:
        resume_status_text = f"Connected: {candidate_ctx.get('name', 'Candidate')}" if has_resume else "Resume auto-linked via chat (+)"

        st.html(f"""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 280px; text-align: center; margin: 4vh 0 2vh 0;">
            <h1 style="font-size: 2.35rem; font-weight: 600; color: var(--sh-text, #ffffff); letter-spacing: -0.025em; margin: 0 0 0.85rem 0;">
                What's on the agenda today?
            </h1>
            <p style="color: var(--sh-text-muted, #94a3b8); font-size: 1.02rem; max-width: 540px; margin: 0 auto; line-height: 1.55;">
                Ask anything freely about your career path, behavioral interviews, salary negotiation, or technical roadmaps.
            </p>
            <div style="display: flex; gap: 0.6rem; align-items: center; justify-content: center; margin-top: 1.4rem;">
                <span style="display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; border-radius: 9999px; font-size: 0.78rem; font-weight: 500; background: var(--sh-surface, rgba(148,163,184,0.1)); border: 1px solid var(--sh-border, rgba(148,163,184,0.2)); color: var(--sh-text-muted, #94a3b8);">
                    {resume_status_text}
                </span>
                <span style="display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; border-radius: 9999px; font-size: 0.78rem; font-weight: 500; background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.25); color: #10b981;">
                    ● Database Synced
                </span>
            </div>
        </div>
        """)

    # Helper for ChatGPT-like live text streaming animation
    def _stream_text_chunks(text: str):
        words = text.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
            time.sleep(0.012)

    # 5. Chat History Loop
    for idx, msg in enumerate(chat_history):
        role = msg.get("role", "user")
        avatar_icon = ":material/account_circle:" if role == "user" else ":material/auto_awesome:"
        with st.chat_message(role, avatar=avatar_icon):
            # Render thinking block if present
            if role == "assistant" and msg.get("thinking"):
                with st.expander("Thought process", expanded=False):
                    st.markdown(msg["thinking"])

            st.markdown(msg.get("content", ""))

            # Citations block
            if role == "assistant" and msg.get("citations"):
                with st.expander(f"Sources ({len(msg['citations'])} documents)", expanded=False):
                    for c in msg["citations"]:
                        st.markdown(f"• **{c.get('source_title', 'Document')}** (Chunk {c.get('chunk_index', 0)})")
                        if c.get("snippet"):
                            st.caption(f"Excerpt: *\"{c['snippet']}...\"*")

                # Feedback telemetry
                f_col1, f_col2, _ = st.columns([1, 1, 4])
                with f_col1:
                    if st.button("Helpful", key=f"f_help_{idx}", help="Rate this response as helpful"):
                        sources = [c.get("source_title", "") for c in msg.get("citations", [])]
                        FeedbackManager.record_mentor_feedback(msg.get("question", ""), msg.get("content", ""), "helpful", sources)
                        st.toast("Feedback recorded.")
                with f_col2:
                    if st.button("Not helpful", key=f"f_unhelp_{idx}", help="Rate this response as unhelpful"):
                        sources = [c.get("source_title", "") for c in msg.get("citations", [])]
                        FeedbackManager.record_mentor_feedback(msg.get("question", ""), msg.get("content", ""), "not_helpful", sources)
                        st.toast("Feedback recorded.")

    # 6. Floating Chat Input with Native Attachment (+) Support
    prompt_submission = st.chat_input(
        "Ask anything",
        accept_file=True,
        file_type=["pdf", "docx", "txt"],
    )

    if prompt_submission:
        user_text = ""
        attached_files = []

        if hasattr(prompt_submission, "text"):
            user_text = (prompt_submission.text or "").strip()
            attached_files = getattr(prompt_submission, "files", []) or []
        else:
            user_text = str(prompt_submission).strip()

        # Handle attached file if user uploaded via the + icon
        if attached_files and len(attached_files) > 0:
            first_file = attached_files[0]
            try:
                file_bytes = first_file.read()
                doc_info = load_document(file_bytes, filename=first_file.name)
                st.session_state.uploaded_file_name = first_file.name
                st.session_state.extracted_resume_text = doc_info["text"]

                parsed_prof = parse_resume(doc_info["text"], api_key=AppStateManager.get_api_key())
                new_container = ProfileReviewManager.initialize_review(parsed_prof)
                st.session_state.human_profile_container = new_container
                AppStateManager.set_workflow_state(WorkflowState.PROFILE_REVIEW)
                AppStateManager.invalidate_downstream()

                # Refresh candidate context & memories in database
                candidate_ctx = CandidateContextManager.extract_from_session_state(st.session_state)
                cand_name = candidate_ctx.get("name", "Candidate")
                cand_role = candidate_ctx.get("target_role", "Engineering / Tech")
                for init_mem in CandidateContextManager.get_initial_memories(candidate_ctx):
                    MentorMemoryManager.add_memory(init_mem)

                AuditLogger.log_event("RESUME_ATTACHED_VIA_CHAT_INPUT", "USER", "SUCCESS", {"filename": first_file.name})
                st.toast(f"Attached and parsed '{first_file.name}'!")
            except Exception as ex:
                st.warning(f"Could not parse attached document: {ex}")

        # If user only uploaded a file without a prompt, formulate a natural onboarding question
        if not user_text and attached_files:
            user_text = f"I've attached my resume ({attached_files[0].name}). Please analyze my background, strengths, and target career trajectory."

        if user_text:
            session_id = st.session_state.mentor_session_id
            now_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            # Append user message to state and persist to database
            st.session_state.mentor_chat_history.append({
                "role": "user",
                "content": user_text,
                "timestamp": now_ts,
            })
            MentorDatabaseManager.save_message(
                session_id=session_id,
                role="user",
                content=user_text,
                candidate_name=cand_name,
                target_role=cand_role,
            )

            with st.chat_message("user", avatar=":material/account_circle:"):
                st.markdown(user_text)

            # Generate AI response with typing indicator
            with st.chat_message("assistant", avatar=":material/auto_awesome:"):
                rag_chain = MentorRAGChain(api_key=AppStateManager.get_api_key())

                # Show animated typing dots while generating
                typing_placeholder = st.empty()
                typing_placeholder.html(
                    '<div class="sh-typing-dots"><span></span><span></span><span></span></div>'
                )

                try:
                    response = rag_chain.answer_question(
                        question=user_text,
                        chat_history=st.session_state.mentor_chat_history,
                        candidate_context=candidate_ctx,
                        candidate_memory=MentorMemoryManager.get_memories(),
                        enable_thinking=st.session_state.get("mentor_think_mode", False),
                    )
                except Exception as exc:
                    logger.error(f"Mentor query failed: {exc}", exc_info=True)
                    response = MentorResponse(
                        question=user_text,
                        answer="The career mentor is temporarily unavailable. Please verify your connection or Gemini API key and try again.",
                        citations=[],
                        is_grounded=False,
                        refusal=True,
                    )

                # Clear typing dots and stream the response text
                typing_placeholder.empty()

                # Animated live text streaming
                st.write_stream(_stream_text_chunks(response.answer))

                if response.citations:
                    with st.expander(f"Sources ({len(response.citations)} documents)", expanded=False):
                        for c in response.citations:
                            st.markdown(f"• **{c.source_title}**")
                            if c.snippet:
                                st.caption(f"Excerpt: *\"{c.snippet}...\"*")

                # Store assistant response in history and persist to database
                citations_dict = [c.model_dump() for c in response.citations]
                st.session_state.mentor_chat_history.append({
                    "role": "assistant",
                    "content": response.answer,
                    "question": user_text,
                    "thinking": response.thinking,
                    "citations": citations_dict,
                    "timestamp": now_ts,
                })

                MentorDatabaseManager.save_message(
                    session_id=session_id,
                    role="assistant",
                    content=response.answer,
                    thinking=response.thinking,
                    citations=citations_dict,
                    candidate_name=cand_name,
                    target_role=cand_role,
                )

                # Autonomous ChatGPT-style candidate memory extraction
                added_mems = MentorMemoryManager.process_turn_autonomously(
                    user_text=user_text,
                    assistant_text=response.answer,
                    api_key=AppStateManager.get_api_key(),
                )
                if added_mems:
                    st.toast(f"Remembered {len(added_mems)} new fact(s) in database.")

                AuditLogger.log_event("MENTOR_QUERY_ANSWERED", "AI", "SUCCESS", {
                    "question": user_text,
                    "is_grounded": response.is_grounded,
                    "refusal": response.refusal,
                    "citations_count": len(response.citations),
                    "session_id": session_id,
                })
                st.rerun()


__all__ = ["render_mentor_chat"]
