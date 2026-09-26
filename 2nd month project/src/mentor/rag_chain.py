import logging
from typing import List, Optional, Dict, Any
from google.genai import types

from src.config import settings, get_gemini_client
from src.models.schemas import MentorResponse, MentorCitation
from src.mentor.retriever import MentorRetriever
from src.mentor.prompts import MENTOR_SYSTEM_PROMPT, MENTOR_USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


class MentorRAGChain:
    """
    RAG chain for conversational AI career mentoring.
    Combines retrieved career knowledge, candidate resume context, and multi-turn dialogue.
    """

    def __init__(
        self,
        retriever: Optional[MentorRetriever] = None,
        api_key: Optional[str] = None,
    ):
        self.retriever = retriever or MentorRetriever()
        self.api_key = api_key or settings.GEMINI_API_KEY

    def answer_question(
        self,
        question: str,
        chat_history: Optional[List[Dict[str, Any]]] = None,
        candidate_context: Optional[Dict[str, Any]] = None,
        candidate_memory: Optional[Any] = None,
        model_name: Optional[str] = None,
        top_k: int = 4,
        enable_thinking: bool = False,
    ) -> MentorResponse:
        from src.safety.guardrails import SafetyGuardrails
        from src.mentor.prompts import MENTOR_THINKING_INSTRUCTION

        # 1. Evaluate input safety & scope guardrails
        is_safe, rejection_reason = SafetyGuardrails.evaluate_input(question)
        if not is_safe:
            return MentorResponse(
                question=question,
                answer=rejection_reason,
                citations=[],
                is_grounded=False,
                refusal=True,
            )

        # 2. Detect casual/greeting messages to skip expensive retrieval & save tokens
        _lower_q = question.strip().lower().rstrip("!?.,")
        _casual_tokens = {"hi", "hello", "hey", "thanks", "thank you", "ok", "okay",
                          "sure", "yes", "no", "bye", "goodbye", "good morning",
                          "good evening", "good night", "what's up", "sup", "yo",
                          "how are you", "whats up"}
        is_casual = _lower_q in _casual_tokens or len(_lower_q.split()) <= 2

        # Only retrieve knowledge base documents for substantive career queries
        # Cap top_k to 3 for token efficiency
        if is_casual:
            chunks = []
        else:
            chunks = self.retriever.retrieve(question, top_k=min(top_k, 3), min_score=0.20)

        # Detect unsupported corporate factual queries absent from documents
        has_resume = bool(candidate_context and candidate_context.get("has_resume"))

        if not chunks and not has_resume and not is_casual:
            return MentorResponse(
                question=question,
                answer="I don't know based on the available documents. The SmartHire knowledge base currently has no verified information on this specific topic.",
                citations=[],
                is_grounded=False,
                refusal=True,
            )

        # Format context chunks with strict character clipping for token optimization
        context_parts = []
        citations: List[MentorCitation] = []
        for i, chunk in enumerate(chunks[:3], start=1):
            source_file = chunk.get("filename", "document.txt")
            source_title = chunk.get("source_title", source_file)
            snippet = chunk.get("snippet", chunk.get("text", ""))[:180]
            # Clip chunk text to 350 chars max to minimize prompt token footprint
            full_text = (chunk.get("text") or snippet)[:350]

            context_parts.append(
                f"[Doc {i}]: {source_title} ({source_file})\n{full_text}"
            )
            citations.append(
                MentorCitation(
                    source_title=source_title,
                    chunk_index=chunk.get("chunk_index", 0),
                    snippet=snippet,
                )
            )

        context_str = "\n\n---\n\n".join(context_parts) if context_parts else "No specific documents retrieved."

        # Format candidate dossier with token clipping
        candidate_dossier = (
            candidate_context.get("formatted_prompt_block", "No candidate resume uploaded yet.")
            if candidate_context
            else "No candidate resume uploaded yet."
        )
        if len(candidate_dossier) > 900:
            candidate_dossier = candidate_dossier[:900] + "\n[Resume truncated for token efficiency]"

        # Format persistent candidate memory facts (top 6 facts max)
        if candidate_memory:
            if isinstance(candidate_memory, list):
                memory_lines = [f"• {m}" for m in candidate_memory[:6] if m]
                memory_str = "\n".join(memory_lines) if memory_lines else "None recorded."
            elif isinstance(candidate_memory, dict):
                memory_lines = [f"• {k}: {v}" for k, v in list(candidate_memory.items())[:6] if v]
                memory_str = "\n".join(memory_lines) if memory_lines else "None recorded."
            else:
                memory_str = str(candidate_memory)[:300]
        else:
            memory_str = "None recorded."

        # Format multi-turn conversation history (token optimized: max 4 turns, clipped text)
        history_lines = []
        if chat_history:
            recent_turns = chat_history[-2:] if is_casual else chat_history[-4:]
            for turn in recent_turns:
                role = "User" if turn.get("role") == "user" else "Mentor"
                content = str(turn.get("content", "")).strip()
                if content:
                    # Clip history entries to avoid prompt inflation
                    max_h = 80 if is_casual else (220 if role == "Mentor" else 180)
                    if len(content) > max_h:
                        content = content[:max_h] + "..."
                    history_lines.append(f"{role}: {content}")
        history_str = "\n".join(history_lines) if history_lines else "None."

        # Assemble full user prompt
        user_prompt = MENTOR_USER_PROMPT_TEMPLATE.format(
            candidate_dossier=candidate_dossier,
            candidate_memory=memory_str,
            conversation_history=history_str,
            question=question,
            context=context_str,
        )

        if enable_thinking:
            user_prompt += f"\n\n{MENTOR_THINKING_INSTRUCTION}"

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required for the Career Mentor.")

        try:
            answer = self._call_gemini_rag(
                user_prompt,
                model_name=model_name,
                is_casual=is_casual,
                enable_thinking=enable_thinking,
            )
        except Exception as exc:
            logger.warning(f"Gemini API call failed ({exc}). Returning safe refusal.")
            return MentorResponse(
                question=question,
                answer="I don't know based on the available documents. The SmartHire knowledge base currently has no verified information on this specific topic.",
                citations=[],
                is_grounded=False,
                refusal=True,
            )

        # Parse thinking block if present
        thinking_text: Optional[str] = None
        if "<thinking>" in answer:
            import re
            m = re.search(r"<thinking>(.*?)</thinking>", answer, flags=re.DOTALL)
            if m:
                thinking_text = m.group(1).strip()
                answer = re.sub(r"<thinking>.*?</thinking>", "", answer, flags=re.DOTALL).strip()

        is_refusal = "i don't know based on the available documents" in answer.lower()

        # Strip citations for casual messages — no documents should be cited for greetings
        if is_casual:
            citations = []

        return MentorResponse(
            question=question,
            answer=answer,
            citations=citations,
            is_grounded=not is_refusal,
            refusal=is_refusal,
            thinking=thinking_text,
        )


    def _call_gemini_rag(
        self,
        prompt: str,
        model_name: Optional[str] = None,
        is_casual: bool = False,
        enable_thinking: bool = False,
    ) -> str:
        import time
        from google.genai.errors import ServerError, ClientError

        client = get_gemini_client(api_key=self.api_key)
        target_model = model_name or settings.GEMINI_MODEL
        candidate_models = ["gemini-flash-latest", target_model, "gemini-3.6-flash", "gemini-3.1-flash-lite"]

        # Strict token budgeting: 100 for casual, 1000 for thinking mode, 450 for normal queries
        token_budget = 100 if is_casual else (1000 if enable_thinking else 450)

        config = types.GenerateContentConfig(
            system_instruction=MENTOR_SYSTEM_PROMPT,
            temperature=0.35,
            max_output_tokens=token_budget,
        )

        last_error = None
        for model in candidate_models:
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config,
                )
                return response.text.strip()
            except (ServerError, ClientError) as err:
                last_error = err
                logger.warning(f"Gemini {model} error ({type(err).__name__}): {err}. Trying next candidate model...")
                continue
            except Exception as exc:
                last_error = exc
                break

        if last_error:
            raise last_error
        return "I apologize, but the career mentor is temporarily unavailable. Please try again in a moment."


__all__ = ["MentorRAGChain"]
