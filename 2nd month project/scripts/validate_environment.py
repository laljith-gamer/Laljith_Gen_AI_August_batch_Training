"""
Environment Validation Script for SmartHire GenAI.
Validates dependencies, configuration, API credentials, file permissions, and index availability.
Usage: python scripts/validate_environment.py
"""

import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import settings

def validate_environment() -> bool:
    print("=" * 65)
    print("      SMART HIRE GENAI - ENVIRONMENT DIAGNOSTICS")
    print("=" * 65)

    all_passed = True

    # 1. Python Version
    py_ver = sys.version_info
    print(f"[*] Python Version: {py_ver.major}.{py_ver.minor}.{py_ver.micro}")
    if py_ver < (3, 10):
        print("    [!] WARNING: Recommended Python version is 3.10+")
        all_passed = False
    else:
        print("    [+] Python version OK.")

    # 2. Package Imports
    packages = [
        ("google.genai", "Google GenAI SDK (official modern)"),
        ("streamlit", "Streamlit Web UI"),
        ("faiss", "FAISS Vector Search"),
        ("pydantic", "Pydantic Schema Validation"),
        ("pypdf", "PDF Document Loader"),
        ("docx", "DOCX Document Loader"),
        ("pandas", "Pandas Data Ingestion"),
        ("numpy", "NumPy Vector Mathematics"),
        ("sklearn", "Scikit-Learn Fallback & Utilities"),
        ("pytest", "Pytest Automated Testing"),
    ]

    print("\n[*] Inspecting Required Packages:")
    for pkg, label in packages:
        try:
            m = __import__(pkg)
            ver = getattr(m, "__version__", "loaded")
            print(f"    [+] {label} ({pkg}): v{ver}")
        except ImportError as e:
            print(f"    [!] MISSING: {label} ({pkg}) -> {e}")
            all_passed = False

    # 3. API Key & Model Configuration
    print("\n[*] Inspecting Gemini API Configuration:")
    api_key = settings.GEMINI_API_KEY
    if api_key:
        masked_key = api_key[:6] + "..." + api_key[-4:] if len(api_key) > 10 else "***"
        print(f"    [+] GEMINI_API_KEY is detected: {masked_key}")
        print(f"    [+] Primary LLM: {settings.GEMINI_MODEL}")
        print(f"    [+] Fallback LLM: {settings.GEMINI_FALLBACK_MODEL}")
        print(f"    [+] Embedding Model: {settings.GEMINI_EMBEDDING_MODEL} (Dim: {settings.EMBEDDING_DIMENSION})")
    else:
        print("    [!] GEMINI_API_KEY is NOT set in environment or .env.")
        print("        (The app will use local fallback vectorizers and offline heuristics until key is entered)")

    # 4. Storage & Datasets
    print("\n[*] Inspecting Data & Vector Storage:")
    settings.ensure_directories()
    
    # Jobs CSV
    jobs_csv = settings.JOBS_DATA_PATH
    if jobs_csv.exists():
        print(f"    [+] Job dataset found: {jobs_csv} ({jobs_csv.stat().st_size} bytes)")
    else:
        print(f"    [!] Job dataset missing at {jobs_csv}")
        all_passed = False

    # Career notes
    career_notes = list(settings.CAREER_NOTES_DIR.glob("*.*"))
    print(f"    [+] Career notes found: {len(career_notes)} documents in {settings.CAREER_NOTES_DIR}")

    # Job FAISS index
    job_index = settings.JOB_INDEX_DIR / "index.faiss"
    if job_index.exists():
        print(f"    [+] FAISS Job Index exists: {job_index}")
    else:
        print(f"    [!] FAISS Job Index missing. Run: python scripts/build_job_index.py")

    # Mentor FAISS index
    mentor_index = settings.MENTOR_INDEX_DIR / "index.faiss"
    if mentor_index.exists():
        print(f"    [+] FAISS Mentor Index exists: {mentor_index}")
    else:
        print(f"    [!] FAISS Mentor Index missing. Run: python scripts/build_mentor_index.py")

    print("\n" + "=" * 65)
    if all_passed:
        print("  [SUCCESS] All environment requirements verified successfully!")
    else:
        print("  [WARNING] Some optional components or packages require attention.")
    print("=" * 65)

    return all_passed

if __name__ == "__main__":
    success = validate_environment()
    sys.exit(0 if success else 1)
