import pytest
from src.models.schemas import ResumeProfile, ExperienceItem, EducationItem
from src.parsing.loader import clean_text
from src.parsing.chunker import split_into_chunks


def test_clean_text():
    raw = "John   Doe\r\n\r\n\r\nSoftware   Engineer\t\twith Python."
    cleaned = clean_text(raw)
    assert "John Doe" in cleaned
    assert "\r" not in cleaned
    assert "\t\t" not in cleaned
    assert "\n\n\n" not in cleaned


def test_chunker_metadata():
    text = "Machine learning engineer building production RAG pipelines with FAISS and Gemini. " * 10
    chunks = split_into_chunks(text, metadata={"filename": "resume.pdf"}, chunk_size=100, chunk_overlap=20)
    assert len(chunks) > 1
    assert chunks[0]["metadata"]["filename"] == "resume.pdf"
    assert "chunk_index" in chunks[0]["metadata"]
    assert "chunk_id" in chunks[0]


def test_pydantic_schema_validation():
    data = {
        "name": "Jane Smith",
        "email": "jane.smith@example.com",
        "skills": ["Python", "Docker", "FastAPI"],
        "experience": [
            {
                "company": "Tech Corp",
                "role": "Senior Backend Developer",
                "start_date": "2021",
                "end_date": "Present",
                "description": "Developed microservices.",
                "technologies": ["Python", "FastAPI"],
            }
        ],
        "education": [
            {
                "institution": "State University",
                "degree": "B.S. Computer Science",
                "field": "Computer Science",
            }
        ],
    }
    profile = ResumeProfile(**data)
    assert profile.name == "Jane Smith"
    assert profile.email == "jane.smith@example.com"
    assert len(profile.skills) == 3
    assert profile.experience[0].role == "Senior Backend Developer"
    assert profile.years_of_experience is None
