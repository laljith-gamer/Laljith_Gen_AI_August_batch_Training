"""
Download the external Kaggle datasets used by SmartHire.

Run from:
    2nd month project/

Examples:
    python scripts/download_kaggle_datasets.py --dataset resume,naukri
    python scripts/download_kaggle_datasets.py --dataset linkedin
    python scripts/download_kaggle_datasets.py --dataset all

Prerequisite:
    Install/authenticate the official Kaggle CLI:
        python -m pip install -U kaggle
        kaggle auth login
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_ROOT = PROJECT_ROOT / "data" / "raw" / "kaggle"

DATASETS = {
    "resume": {
        "slug": "snehaanbhawal/resume-dataset",
        "target": RAW_ROOT / "resumes",
    },
    "naukri": {
        "slug": "PromptCloudHQ/jobs-on-naukricom",
        "target": RAW_ROOT / "jobs",
    },
    "linkedin": {
        "slug": "arshkon/linkedin-job-postings",
        "target": RAW_ROOT / "linkedin",
    },
}


def run_kaggle_download(slug: str, target: Path, file_name: str | None = None) -> None:
    target.mkdir(parents=True, exist_ok=True)

    command = [
        "kaggle",
        "datasets",
        "download",
        "-d",
        slug,
        "-p",
        str(target),
        "--unzip",
        "-o",
    ]

    if file_name:
        command.extend(["-f", file_name])

    print(f"\n[DOWNLOAD] {slug}")
    print(f"[TARGET]   {target}")

    try:
        subprocess.run(command, check=True)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "The Kaggle CLI is not installed or is not on PATH. "
            "Install it with: python -m pip install -U kaggle"
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"Kaggle download failed for {slug} with exit code {exc.returncode}. "
            "Authenticate first with: kaggle auth login"
        ) from exc


def canonicalize_resume_dataset(target: Path) -> Path:
    """
    Kaggle currently stores the CSV under Resume/Resume.csv.
    Copy it to a stable project-local path while preserving the downloaded tree.
    """
    candidates = [
        target / "Resume" / "Resume.csv",
        target / "Resume.csv",
    ]

    source = next((p for p in candidates if p.exists()), None)
    if source is None:
        raise FileNotFoundError(
            f"Resume.csv was not found under {target}. "
            "Inspect the downloaded Kaggle archive layout."
        )

    canonical = target / "Resume.csv"
    if source.resolve() != canonical.resolve():
        shutil.copy2(source, canonical)

    return canonical


def validate_csv_header(path: Path, expected: set[str], label: str) -> None:
    import csv

    if not path.exists():
        raise FileNotFoundError(f"{label} file not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = {value.strip() for value in next(reader, [])}

    missing = expected - header
    if missing:
        raise ValueError(
            f"{label} is missing expected columns: {sorted(missing)}. "
            f"Found columns: {sorted(header)}"
        )


def find_first(target: Path, names: set[str]) -> Path | None:
    for name in names:
        direct = target / name
        if direct.exists():
            return direct

    for candidate in target.rglob("*"):
        if candidate.is_file() and candidate.name in names:
            return candidate

    return None


def print_size(path: Path) -> None:
    if path.is_file():
        size_mb = path.stat().st_size / (1024 * 1024)
        print(f"[READY]    {path} ({size_mb:.2f} MB)")
        return

    total = sum(p.stat().st_size for p in path.rglob("*") if p.is_file())
    size_mb = total / (1024 * 1024)
    print(f"[READY]    {path}/ ({size_mb:.2f} MB extracted)")


def download_resume() -> None:
    target = DATASETS["resume"]["target"]

    # Download only the CSV required by ResumeDatasetManager by default.
    run_kaggle_download(
        DATASETS["resume"]["slug"],
        target,
        file_name="Resume/Resume.csv",
    )

    canonical = canonicalize_resume_dataset(target)
    validate_csv_header(
        canonical,
        {"ID", "Resume_str", "Resume_html", "Category"},
        "Resume dataset",
    )
    print_size(canonical)


def download_naukri() -> None:
    target = DATASETS["naukri"]["target"]
    run_kaggle_download(DATASETS["naukri"]["slug"], target)

    csv_path = find_first(target, {"naukri_com-job_sample.csv"})
    if csv_path is None:
        raise FileNotFoundError(
            f"naukri_com-job_sample.csv was not found under {target}"
        )

    canonical = target / "naukri_com-job_sample.csv"
    if csv_path.resolve() != canonical.resolve():
        shutil.copy2(csv_path, canonical)

    validate_csv_header(
        canonical,
        {"company", "jobid", "joblocation_address", "jobtitle", "skills", "jobdescription"},
        "Naukri dataset",
    )
    print_size(canonical)


def download_linkedin() -> None:
    target = DATASETS["linkedin"]["target"]
    run_kaggle_download(DATASETS["linkedin"]["slug"], target)

    postings = find_first(target, {"postings.csv", "job_postings.csv"})
    if postings is None:
        raise FileNotFoundError(
            f"No LinkedIn postings CSV was found under {target}"
        )

    print_size(target)
    print(f"[POSTINGS] {postings}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download SmartHire's external Kaggle datasets into data/raw/kaggle/"
    )
    parser.add_argument(
        "--dataset",
        required=True,
        help="Comma-separated values: resume, naukri, linkedin, all",
    )
    args = parser.parse_args()

    requested = [value.strip().lower() for value in args.dataset.split(",") if value.strip()]
    if "all" in requested:
        requested = list(DATASETS)

    unknown = sorted(set(requested) - set(DATASETS))
    if unknown:
        parser.error(f"Unknown dataset(s): {', '.join(unknown)}")

    # Preserve order but avoid duplicate downloads.
    requested = list(dict.fromkeys(requested))

    try:
        for dataset in requested:
            if dataset == "resume":
                download_resume()
            elif dataset == "naukri":
                download_naukri()
            elif dataset == "linkedin":
                download_linkedin()
    except Exception as exc:
        print(f"\n[ERROR] {exc}", file=sys.stderr)
        return 1

    print("\n[DONE] Requested Kaggle datasets are available under:")
    print(f"       {RAW_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
