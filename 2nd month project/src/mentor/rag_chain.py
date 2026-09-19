"""
End-to-end RAG Chain for the AI Career Mentor.
Combines Guardrails, Retrieval, Context Grounding, Gemini 3.8 Flash, and Source Citations.
"""

import re
import logging
from typing import List, Optional, Dict, Any
from google.genai import types

from src.config import settings, get_gemini_client
from src.models.schemas import MentorResponse, MentorCitation
from src.mentor.retriever import MentorRetriever
from src.mentor.prompts import MENTOR_SYSTEM_PROMPT, MENTOR_USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

class MentorRAGChain:
    """Executes grounded RAG pipeline for career mentor queries."""

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
        chat_history: Optional[List[Dict[str, str]]] = None,
        model_name: Optional[str] = None,
        top_k: int = 4,
    ) -> MentorResponse:
        """
        Execute full grounded RAG response for a career query.
        """
        from src.safety.guardrails import SafetyGuardrails

        # 1. Guardrail Safety Check
        is_safe, rejection_reason = SafetyGuardrails.evaluate_input(question)
        if not is_safe:
            return MentorResponse(
                question=question,
                answer=rejection_reason,
                citations=[],
                is_grounded=False,
                refusal=True,
            )

        # 2. Retrieve Grounding Context
        chunks = self.retriever.retrieve(question, top_k=top_k, min_score=0.20)

        # 3. Insufficient Context Refusal Check
        if not chunks:
            return MentorResponse(
                question=question,
                answer="I don't know based on the available documents. The SmartHire knowledge base currently has no verified information on this specific topic.",
                citations=[],
                is_grounded=False,
                refusal=True,
            )

        # 4. Context Assembly
        context_parts = []
        citations: List[MentorCitation] = []
        for i, chunk in enumerate(chunks, start=1):
            source_file = chunk.get("filename", "document.txt")
            source_title = chunk.get("source_title", source_file)
            snippet = chunk.get("snippet", chunk.get("text", ""))[:200]
            
            context_parts.append(
                f"[Document {i}]: {source_title} (File: {source_file})\n{chunk.get('text', snippet)}"
            )

            citations.append(
                MentorCitation(
                    source_title=source_title,
                    chunk_index=chunk.get("chunk_index", 0),
                    snippet=snippet,
                )
            )

        context_str = "\n\n---\n\n".join(context_parts)
        user_prompt = MENTOR_USER_PROMPT_TEMPLATE.format(
            question=question,
            context=context_str,
        )

        # 5. Gemini Generation
        if self.api_key:
            try:
                answer = self._call_gemini_rag(user_prompt, model_name=model_name)
                # Check for model explicit refusal
                is_refusal = "i don't know based on the available documents" in answer.lower()
                return MentorResponse(
                    question=question,
                    answer=answer,
                    citations=citations,
                    is_grounded=not is_refusal,
                    refusal=is_refusal,
                )
            except Exception as exc:
                logger.warning(f"Gemini RAG call encountered error: {exc}. Using deterministic grounded response.")
                return self._fallback_grounded_answer(question, chunks, citations)
        else:
            return self._fallback_grounded_answer(question, chunks, citations)

    def _call_gemini_rag(self, prompt: str, model_name: Optional[str] = None) -> str:
        client = get_gemini_client(api_key=self.api_key)
        target_model = model_name or settings.GEMINI_MODEL

        config = types.GenerateContentConfig(
            system_instruction=MENTOR_SYSTEM_PROMPT,
            temperature=0.2,
        )

        try:
            response = client.models.generate_content(
                model=target_model,
                contents=prompt,
                config=config,
            )
            return response.text.strip()
        except Exception as exc:
            fallback = settings.GEMINI_FALLBACK_MODEL
            if fallback and fallback != target_model:
                logger.warning(f"Retrying RAG generation with fallback {fallback}...")
                response = client.models.generate_content(
                    model=fallback,
                    contents=prompt,
                    config=config,
                )
                return response.text.strip()
            raise exc

    def _fallback_grounded_answer(
        self,
        question: str,
        chunks: List[Dict[str, Any]],
        citations: List[MentorCitation],
    ) -> MentorResponse:
        """Deterministic answer constructed directly from retrieved excerpts for offline mode."""
        primary_chunk = chunks[0]
        context_text = primary_chunk.get("text", primary_chunk.get("snippet", ""))

        # Lexical keyword verification: if significant question terms don't appear in context, refuse
        q_words = [w.lower() for w in re.findall(r"\b[a-zA-Z]{4,}\b", question)]
        # Filter out common question stop words
        stop_words = {"what", "when", "where", "which", "could", "would", "should", "exact", "available", "information", "tell"}
        key_q_words = [w for w in q_words if w not in stop_words]
        
        lower_context = context_text.lower()
        has_overlap = any(kw in lower_context for kw in key_q_words)

        if key_q_words and not has_overlap:
            return MentorResponse(
                question=question,
                answer="I don't know based on the available documents. The retrieved SmartHire documents do not contain verified information on this topic.",
                citations=citations,
                is_grounded=False,
                refusal=True,
            )

        excerpt = context_text[:300]
        answer = (
            f"Based on the SmartHire knowledge base:\n\n"
            f"{excerpt}\n\n"
            f"To pursue this pathway, review the full recommendations in {primary_chunk.get('filename')}.\n\n"
            f"Based on:\n"
            + "\n".join([f"- {c.source_title}" for c in citations])
        )
        return MentorResponse(
            question=question,
            answer=answer,
            citations=citations,
            is_grounded=True,
            refusal=False,
        )
