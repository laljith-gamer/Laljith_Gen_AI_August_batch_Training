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

def test_dynamic_json_heuristic_generation_across_categories():
    """Verify heuristic generation guarantees valid required fields across diverse domains."""
    sample_categories = ["INFORMATION-TECHNOLOGY", "HR", "FINANCE"]
    
    for cat in sample_categories:
        resumes = ResumeDatasetManager.get_resumes_by_category(cat, limit=1)
        assert len(resumes) > 0
        sample_id = resumes[0]["id"]
        full_record = ResumeDatasetManager.get_resume(sample_id)
        assert full_record is not None

        profile_json = DynamicJSONGenerator._generate_with_heuristics(
            resume_id=full_record["id"],
            cleaned_text=full_record["cleaned_text"],
            category=full_record["category"],
        )

        # Assert all required fields are satisfied
        assert profile_json.id == sample_id
        assert profile_json.category == cat
        assert len(profile_json.name) > 0
        assert len(profile_json.target_role) > 0
        assert profile_json.years_of_experience >= 0.0
        assert len(profile_json.skills) >= 1
        assert len(profile_json.summary) >= 5
        assert isinstance(profile_json.experience, list)
        assert isinstance(profile_json.education, list)
        assert "validation_status" in profile_json.metadata

        # Assert serialization
        json_str = profile_json.to_json_str()
        assert f'"{sample_id}"' in json_str

        # Assert conversion to internal ResumeProfile
        internal_profile = profile_json.to_resume_profile()
        assert isinstance(internal_profile, ResumeProfile)
        assert internal_profile.target_role == profile_json.target_role
        assert len(internal_profile.skills) >= 1
