import logging
from typing import List, Optional, Dict, Any
from google.genai import types

from src.config import settings, get_gemini_client
from src.models.schemas import MentorResponse, MentorCitation
from src.mentor.retriever import MentorRetriever
from src.mentor.prompts import MENTOR_SYSTEM_PROMPT, MENTOR_USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


class MentorRAGChain:

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
        from src.safety.guardrails import SafetyGuardrails

        is_safe, rejection_reason = SafetyGuardrails.evaluate_input(question)
        if not is_safe:
            return MentorResponse(
                question=question,
                answer=rejection_reason,
                citations=[],
                is_grounded=False,
                refusal=True,
            )

        chunks = self.retriever.retrieve(question, top_k=top_k, min_score=0.20)

        if not chunks:
            return MentorResponse(
                question=question,
                answer="I don't know based on the available documents. The SmartHire knowledge base currently has no verified information on this specific topic.",
                citations=[],
                is_grounded=False,
                refusal=True,
            )

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

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required for the Career Mentor.")

        answer = self._call_gemini_rag(user_prompt, model_name=model_name)
        is_refusal = "i don't know based on the available documents" in answer.lower()
        return MentorResponse(
            question=question,
            answer=answer,
            citations=citations,
            is_grounded=not is_refusal,
            refusal=is_refusal,
        )

    def _call_gemini_rag(self, prompt: str, model_name: Optional[str] = None) -> str:
        client = get_gemini_client(api_key=self.api_key)
        target_model = model_name or settings.GEMINI_MODEL

        config = types.GenerateContentConfig(
            system_instruction=MENTOR_SYSTEM_PROMPT,
            temperature=0.2,
        )

        response = client.models.generate_content(
            model=target_model,
            contents=prompt,
            config=config,
        )
        return response.text.strip()


__all__ = ["MentorRAGChain"]
