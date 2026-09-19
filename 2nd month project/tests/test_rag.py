"""
Unit tests for AI Career Mentor RAG retriever, grounding, citations, and refusal.
"""

import pytest
from src.mentor.retriever import MentorRetriever
from src.mentor.rag_chain import MentorRAGChain

def test_retriever_returns_grounded_chunks():
    retriever = MentorRetriever()
    query = "What skills are needed for a Data Analyst?"
    chunks = retriever.retrieve(query, top_k=3)
    assert len(chunks) > 0
    top_chunk = chunks[0]
    assert "source_title" in top_chunk
    assert "filename" in top_chunk
    assert "score" in top_chunk
    # Should match either data analyst roadmap or data analyst job
    combined_titles = " ".join([c["source_title"].lower() for c in chunks])
    assert "data analyst" in combined_titles

def test_mentor_rag_chain_answering_and_citations():
    rag_chain = MentorRAGChain()
    query = "Explain the STAR method for behavioral interviews."
    response = rag_chain.answer_question(query)
    
    assert response.is_grounded is True
    assert len(response.citations) > 0
    # Citations must include the interview preparation guide
    citation_files = [c.source_title.lower() for c in response.citations]
    assert any("interview" in title for title in citation_files)
    assert "star" in response.answer.lower()

def test_mentor_rag_refuses_unsupported_knowledge():
    rag_chain = MentorRAGChain()
    # Ask something completely absent from our local knowledge base
    query = "What is the exact dental insurance copay for Acme Corp employees in 2029?"
    response = rag_chain.answer_question(query)
    
    # Should appropriately refuse
    lower_ans = response.answer.lower()
    assert (
        "i don't know" in lower_ans
        or "available documents" in lower_ans
        or response.refusal is True
    )
