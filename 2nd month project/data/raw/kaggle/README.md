# Kaggle raw datasets

This directory is the canonical local location for external datasets used by SmartHire.

## Sources

| Dataset | Kaggle slug | Local path | Role in SmartHire |
|---|---|---|---|
| Resume Dataset | `snehaanbhawal/resume-dataset` | `data/raw/kaggle/resumes/` | Resume explorer / parser dataset |
| Jobs on Naukri.com | `PromptCloudHQ/jobs-on-naukricom` | `data/raw/kaggle/jobs/` | Raw job corpus source |
| LinkedIn Job Postings (2023-2024) | `arshkon/linkedin-job-postings` | `data/raw/kaggle/linkedin/` | Optional larger job corpus / analysis |

The resume dataset contains 2,400+ resumes and exposes `ID`, `Resume_str`, `Resume_html`, and `Category`. The Naukri dataset used by this project is the 22,000-listing Kaggle sample with `naukri_com-job_sample.csv`. The LinkedIn dataset is substantially larger and is kept optional because its current Kaggle snapshot is hundreds of megabytes.

## Download

Authenticate with Kaggle first, then run from the `2nd month project` directory:

```bash
kaggle auth login
python scripts/download_kaggle_datasets.py --dataset resume,naukri
```

To also download the LinkedIn corpus:

```bash
python scripts/download_kaggle_datasets.py --dataset linkedin
```

To download everything:

```bash
python scripts/download_kaggle_datasets.py --dataset all
```

The script validates the expected files and prints their final locations.

## Why these are kept under data/raw

The existing SmartHire files under `data/jobs/` and `data/resumes/` are application-ready/demo assets. Kaggle downloads are kept separately so raw source data is not silently mixed with normalized project data.

Do not commit Kaggle credentials, API tokens, `.env`, or `.kaggle/kaggle.json`.

Large raw datasets should be kept outside normal Git blobs or managed with Git LFS/external object storage. In particular, the current LinkedIn Kaggle snapshot is too large for a normal GitHub file upload.
