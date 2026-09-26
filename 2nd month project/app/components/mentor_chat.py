"""
Interactive AI Career Mentor Chat Component inspired by modern ChatGPT canvas.
Features:
- Minimalist hero: "What's on the agenda today?" with zero canned prompt clutter
- Deep reasoning toggle: "Think" with Streamlit compact status ("Thought for N seconds")
- ChatGPT-style Browser IndexedDB History (Today, Previous 7 Days, Older) with + New Chat
- ChatGPT-style Candidate Memory (persisted in IndexedDB and automatically populated from resume)
- Automatic resume data extraction + native file attachment in chat input
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
from app.components.mentor_storage import MentorIndexedDBManager
from app.components.mentor_memory import MentorMemoryManager

logger = logging.getLogger(__name__)


def _group_sessions_by_date(sessions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group saved sessions into ChatGPT-style buckets: Today, Previous 7 Days, Older."""
    now = datetime.datetime.now(datetime.timezone.utc)
    groups: Dict[str, List[Dict[str, Any]]] = {"Today": [], "Previous 7 Days": [], "Older": []}

    for s in sessions:
        up_str = s.get("updated_at")
        if not up_str:
            groups["Older"].append(s)
            continue
        try:
            dt = datetime.datetime.fromisoformat(up_str.replace("Z", "+00:00"))
            delta = (now - dt).total_seconds()
            if delta < 86400 and dt.date() == now.date():
                groups["Today"].append(s)
            elif delta < 7 * 86400:
                groups["Previous 7 Days"].append(s)
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
        st.session_state.mentor_chat_history = []

    if "mentor_think_mode" not in st.session_state:
        st.session_state.mentor_think_mode = False

    if "mentor_pending_action" not in st.session_state:
        st.session_state.mentor_pending_action = None

    if "mentor_saved_sessions_cache" not in st.session_state:
        st.session_state.mentor_saved_sessions_cache = []

    # Extract candidate context automatically from uploaded resume
    candidate_ctx = CandidateContextManager.extract_from_session_state(st.session_state)
    has_resume = candidate_ctx.get("has_resume", False)

    # Initialize ChatGPT-style candidate memories
    MentorMemoryManager.initialize_memories(candidate_ctx)
    memories = MentorMemoryManager.get_memories()

    # 2. Browser IndexedDB Storage Engine (CCv2 bridge)
    action_override = None
    action_payload = None
    if st.session_state.mentor_pending_action:
        pending = st.session_state.mentor_pending_action
        action_override = pending.get("action")
        action_payload = pending.get("payload")
        st.session_state.mentor_pending_action = None

    storage_result = MentorIndexedDBManager.render_storage_toolbar(
        active_session_id=st.session_state.mentor_session_id,
        messages=st.session_state.mentor_chat_history,
        candidate_summary=candidate_ctx,
        action_override=action_override,
        action_payload=action_payload,
        key="mentor_idb_sync_bar",
    )

    # Reactive synchronization from IndexedDB
    if storage_result:
        # Check for restored session payload
        restored = getattr(storage_result, "restore_session_payload", None)
        if restored and isinstance(restored, dict) and "messages" in restored:
            st.session_state.mentor_chat_history = restored["messages"]
            if restored.get("id"):
                st.session_state.mentor_session_id = restored["id"]
            st.toast(f"Switched to: '{restored.get('title', 'Saved Chat')}'")
            st.rerun()

        # Check for clear trigger
        if getattr(storage_result, "cleared_storage_trigger", None):
            st.session_state.mentor_chat_history = []
            st.session_state.mentor_session_id = f"session_{int(time.time() * 1000)}"
            st.session_state.mentor_saved_sessions_cache = []
            st.toast("Browser chat history cleared.")
            st.rerun()

        # Update cached session list and memories if provided by component state
        saved_list = getattr(storage_result, "saved_sessions", None)
        if isinstance(saved_list, list) and saved_list:
            st.session_state.mentor_saved_sessions_cache = saved_list

        db_memories = getattr(storage_result, "stored_memories", None)
        if isinstance(db_memories, list) and db_memories:
            MentorMemoryManager.sync_from_indexeddb(db_memories)

    # 3. Top Action Toolbar (History + New Chat + Think + Memory)
    col_hist, col_new, col_think, col_mem = st.columns([1.2, 1, 1, 1.2])

    with col_new:
        if st.button("＋ New chat", key="btn_mentor_new_chat", type="secondary", use_container_width=True, help="Start a fresh conversation"):
            st.session_state.mentor_chat_history = []
            st.session_state.mentor_session_id = f"session_{int(time.time() * 1000)}"
            st.toast("Started fresh conversation.")
            st.rerun()

    with col_think:
        think_active = st.session_state.get("mentor_think_mode", False)
        think_type = "primary" if think_active else "secondary"
        if st.button(":material/psychology: Think", key="btn_mentor_think_toggle", type=think_type, use_container_width=True, help="Toggle deep reasoning mode"):
            st.session_state.mentor_think_mode = not think_active
            st.toast(f"Deep reasoning mode: {'ON' if not think_active else 'OFF'}")
            st.rerun()

    with col_hist:
        # History Popover (Grouped by Today, 7 Days, Older)
        saved_sessions = st.session_state.mentor_saved_sessions_cache
        hist_label = f":material/history: History ({len(saved_sessions)})" if saved_sessions else ":material/history: History"
        with st.popover(hist_label, width="stretch", help="Browse and restore saved chat history from IndexedDB"):
            st.markdown("##### Chat History")
            st.caption("Conversations are securely stored inside your browser's IndexedDB.")

            if not saved_sessions:
                st.info("No saved conversations found in browser storage yet. Start chatting to save automatically!")
            else:
                grouped = _group_sessions_by_date(saved_sessions)
                for group_name, sess_list in grouped.items():
                    if sess_list:
                        st.markdown(f"**{group_name}**")
                        for s in sess_list:
                            s_id = s.get("id")
                            s_title = s.get("title") or "Career Discussion"
                            short_title = (s_title[:28] + "...") if len(s_title) > 28 else s_title
                            is_curr = s_id == st.session_state.mentor_session_id

                            row_col1, row_col2 = st.columns([4, 1])
                            with row_col1:
                                btn_type = "primary" if is_curr else "secondary"
                                if st.button(
                                    short_title,
                                    key=f"hist_load_{s_id}",
                                    type=btn_type,
                                    help=f"{s_title}\n({s.get('message_count', 0)} messages)",
                                ):
                                    st.session_state.mentor_pending_action = {
                                        "action": "load_session",
                                        "payload": {"session_id": s_id},
                                    }
                                    st.rerun()
                            with row_col2:
                                if st.button(":material/delete:", key=f"hist_del_{s_id}", help="Delete this chat from browser"):
                                    st.session_state.mentor_pending_action = {
                                        "action": "delete_session",
                                        "payload": {"session_id": s_id},
                                    }
                                    st.session_state.mentor_saved_sessions_cache = [
                                        item for item in saved_sessions if item.get("id") != s_id
                                    ]
                                    if s_id == st.session_state.mentor_session_id:
                                        st.session_state.mentor_chat_history = []
                                        st.session_state.mentor_session_id = f"session_{int(time.time() * 1000)}"
                                    st.toast("Conversation deleted.")
                                    st.rerun()

    with col_mem:
        # Memory Popover (ChatGPT-style Memory)
        active_mems = MentorMemoryManager.get_memories()
        mem_count_label = f":material/psychology: Memory ({len(active_mems)})" if active_mems else ":material/psychology: Memory"
        with st.popover(mem_count_label, width="stretch", help="Manage persistent candidate facts remembered across chats"):
            st.markdown("##### Candidate Memory")
            st.caption("The mentor retains these verified facts across sessions to personalize career guidance.")

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
            if st.button("Save to Memory", key="btn_save_custom_mem") and new_mem_input:
                MentorMemoryManager.add_memory(new_mem_input)
                # Sync to IndexedDB
                st.session_state.mentor_pending_action = {
                    "action": "save_memory",
                    "payload": {
                        "memory_item": {
                            "key": f"mem_{int(time.time() * 1000)}",
                            "fact": new_mem_input,
                            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        }
                    },
                }
                st.toast("Memory updated.")
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
        # Extract text and files from submission
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

                # Refresh candidate context & memories
                candidate_ctx = CandidateContextManager.extract_from_session_state(st.session_state)
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
            # Append user message
            st.session_state.mentor_chat_history.append({
                "role": "user",
                "content": user_text,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })
            with st.chat_message("user", avatar=":material/account_circle:"):
                st.markdown(user_text)

            # Generate AI response with typing indicator
            with st.chat_message("assistant", avatar=":material/auto_awesome:"):
                rag_chain = MentorRAGChain(api_key=AppStateManager.get_api_key())
                t_start = time.time()

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

                # Store assistant response in history
                citations_dict = [c.model_dump() for c in response.citations]
                st.session_state.mentor_chat_history.append({
                    "role": "assistant",
                    "content": response.answer,
                    "question": user_text,
                    "thinking": response.thinking,
                    "citations": citations_dict,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                })

                # Autonomous ChatGPT-style candidate memory extraction
                added_mems = MentorMemoryManager.process_turn_autonomously(
                    user_text=user_text,
                    assistant_text=response.answer,
                    api_key=AppStateManager.get_api_key(),
                )
                if added_mems:
                    st.toast(f"Remembered {len(added_mems)} new fact(s).")
                    for mem in added_mems:
                        st.session_state.mentor_pending_action = {
                            "action": "save_memory",
                            "payload": {
                                "memory_item": {
                                    "key": f"mem_{int(time.time() * 1000)}",
                                    "fact": mem,
                                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                }
                            },
                        }

                AuditLogger.log_event("MENTOR_QUERY_ANSWERED", "AI", "SUCCESS", {
                    "question": user_text,
                    "is_grounded": response.is_grounded,
                    "refusal": response.refusal,
                    "citations_count": len(response.citations),
                    "session_id": st.session_state.mentor_session_id,
                })
                st.rerun()


__all__ = ["render_mentor_chat"]
