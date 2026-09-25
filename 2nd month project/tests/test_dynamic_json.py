"""
Unit tests for Dynamic JSON Generator and Resume Dataset Manager.
Tests schema validation, required fields enforcement, text normalization, and JSON export.
"""

import pytest
from pydantic import ValidationError
from src.data.resume_dataset import ResumeDatasetManager
from src.parsing.dynamic_json import (
    DynamicResumeJSON,
    DynamicJSONGenerator,
    WorkExperienceEntry,
    EducationEntry,
)
from src.models.schemas import ResumeProfile

def test_dataset_manager_loads_categories():
    """Verify that Resume.csv loads cleanly and returns 24 categories."""
    assert ResumeDatasetManager.is_available(), "Resume.csv must be accessible."
    categories = ResumeDatasetManager.get_categories()
    assert len(categories) == 24
    assert "INFORMATION-TECHNOLOGY" in categories
    assert "FINANCE" in categories
    assert "HR" in categories

    counts = ResumeDatasetManager.get_category_counts()
    assert counts["INFORMATION-TECHNOLOGY"] >= 100
    assert counts["FINANCE"] >= 100

def test_dataset_manager_retrieves_resumes_by_category():
    """Verify retrieving sample resumes for a specific industry category."""
    resumes = ResumeDatasetManager.get_resumes_by_category("INFORMATION-TECHNOLOGY", limit=5)
    assert len(resumes) == 5
    for r in resumes:
        assert "id" in r
        assert r["category"] == "INFORMATION-TECHNOLOGY"
        assert "headline" in r
        assert len(r["headline"]) > 0

def test_clean_resume_text_normalizes_unicode():
    """Verify text cleaner replaces corrupted unicode artifacts with bullets."""
    dirty_text = "Software Engineer \ufffd Java Developer \uff0d Spring Boot\n\n\n\n\t\t\tMicroservices"
    cleaned = ResumeDatasetManager.clean_resume_text(dirty_text)
    assert "\ufffd" not in cleaned
    assert "\uff0d" not in cleaned
    assert "•" in cleaned
    assert "\t" not in cleaned

def test_dynamic_json_schema_enforces_required_fields():
    """Verify that missing or invalid required fields trigger Pydantic validation errors."""
    # Empty skills list must fail
    with pytest.raises(ValidationError):
        DynamicResumeJSON(
            id="123",
            category="IT",
            name="Alice",
            target_role="Software Engineer",
            years_of_experience=5.0,
            skills=[],  # INVALID: Empty skills
            summary="Experienced developer with 5 years in software engineering.",
            experience=[],
            education=[],
            metadata={"test": True},
        )

    # Negative years of experience must fail
    with pytest.raises(ValidationError):
        DynamicResumeJSON(
            id="123",
            category="IT",
            name="Alice",
            target_role="Software Engineer",
            years_of_experience=-2.0,  # INVALID: Negative YoE
            skills=["Python"],
            summary="Experienced developer with 5 years in software engineering.",
            experience=[],
            education=[],
            metadata={"test": True},
        )

def test_dynamic_json_schema_conversion():
    """Verify DynamicResumeJSON serialization and conversion to ResumeProfile."""
    profile_json = DynamicResumeJSON(
        id="test_101",
        category="INFORMATION-TECHNOLOGY",
        name="Alex Engineer",
        target_role="Senior Software Engineer",
        years_of_experience=6.5,
        skills=["Python", "FastAPI", "FAISS", "Gemini API"],
        summary="Senior Software Engineer specializing in GenAI and backend microservices.",
        experience=[
            WorkExperienceEntry(
                company="Tech Solutions",
                role="Lead AI Engineer",
                start_date="2021",
                end_date="Present",
                highlights=["Built RAG systems", "Deployed Gemini pipelines"]
            )
        ],
        education=[
            EducationEntry(
                institution="State University",
                degree="B.S. Computer Science",
                year="2020"
            )
        ],
        metadata={"validation_status": "valid"}
    )

    # Assert serialization
    json_str = profile_json.to_json_str()
    assert '"test_101"' in json_str

    # Assert conversion to internal ResumeProfile
    internal_profile = profile_json.to_resume_profile()
    assert isinstance(internal_profile, ResumeProfile)
    assert internal_profile.target_role == profile_json.target_role
    assert len(internal_profile.skills) == 4


