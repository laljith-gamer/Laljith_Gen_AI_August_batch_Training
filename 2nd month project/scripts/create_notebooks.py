"""
Create standard Jupyter notebooks specified in Section 6 of SmartHire_GenAI_Project.pdf
"""

import os
import json
from pathlib import Path

notebooks_dir = Path(__file__).resolve().parent.parent / "notebooks"
notebooks_dir.mkdir(parents=True, exist_ok=True)

def create_nb(cells):
    return {
        "cells": cells,
        "metadata": {
            "language_info": {"name": "python", "version": "3.11"}
        },
        "nbformat": 4,
        "nbformat_minor": 5
    }

# 1. 01_embeddings_explore.ipynb
cells1 = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# SmartHire GenAI — 01: Embeddings Exploration\n",
            "This notebook tests text embeddings generation using Google Gemini and evaluates cosine similarity between queries and job titles."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "import sys\n",
            "sys.path.append('..')\n",
            "import numpy as np\n",
            "from src.search.embed import EmbeddingEngine\n",
            "\n",
            "engine = EmbeddingEngine()\n",
            "print('Embedding engine initialized.')\n"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "texts = [\n",
            "    'Senior Machine Learning Engineer specializing in PyTorch and LLM fine-tuning',\n",
            "    'AI/ML Research Scientist working on Generative AI and diffusion models',\n",
            "    'Lead Frontend Developer experienced in React, TypeScript, and CSS'\n",
            "]\n",
            "\n",
            "vectors = engine.embed_texts(texts)\n",
            "print(f'Generated {len(vectors)} embeddings of dimension: {len(vectors[0])}')\n"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "def cosine_sim(v1, v2):\n",
            "    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))\n",
            "\n",
            "sim_ml_ai = cosine_sim(vectors[0], vectors[1])\n",
            "sim_ml_frontend = cosine_sim(vectors[0], vectors[2])\n",
            "\n",
            "print(f'Similarity (ML Eng vs AI Scientist): {sim_ml_ai:.4f}')\n",
            "print(f'Similarity (ML Eng vs Frontend):     {sim_ml_frontend:.4f}')\n",
            "assert sim_ml_ai > sim_ml_frontend, 'ML roles must have higher similarity than ML vs Frontend'\n"
        ]
    }
]

with open(notebooks_dir / "01_embeddings_explore.ipynb", "w", encoding="utf-8") as f:
    json.dump(create_nb(cells1), f, indent=2)

# 2. 02_build_faiss.ipynb
cells2 = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# SmartHire GenAI — 02: Build FAISS Vector Index\n",
            "Loads the job postings corpus and builds/queries the FAISS vector index."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "import sys\n",
            "sys.path.append('..')\n",
            "import pandas as pd\n",
            "from src.config import settings\n",
            "from src.search.job_search import JobSearchEngine\n",
            "\n",
            "jobs_df = pd.read_csv(settings.JOBS_DATA_PATH)\n",
            "print(f'Loaded {len(jobs_df)} jobs from {settings.JOBS_DATA_PATH}')\n",
            "jobs_df.head(3)\n"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "engine = JobSearchEngine()\n",
            "print(f'FAISS index loaded. Total vectors: {engine.index.ntotal if engine.index else 0}')\n"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "query = 'Python Backend Engineer with FastAPI, PostgreSQL, and Docker'\n",
            "results = engine.search_by_text(query, top_k=3)\n",
            "\n",
            "for idx, m in enumerate(results):\n",
            "    print(f'[{idx+1}] {m.job.title} at {m.job.company} (Score: {m.similarity_score:.3f})')\n"
        ]
    }
]

with open(notebooks_dir / "02_build_faiss.ipynb", "w", encoding="utf-8") as f:
    json.dump(create_nb(cells2), f, indent=2)

# 3. 03_rag_prototype.ipynb
cells3 = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# SmartHire GenAI — 03: Career Mentor RAG Prototype\n",
            "Prototypes grounded question answering over the career notes corpus with strict anti-hallucination refusal."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "import sys\n",
            "sys.path.append('..')\n",
            "from src.mentor.rag_chain import CareerMentorRAG\n",
            "from src.safety.guardrails import SafetyGuardrails\n",
            "\n",
            "mentor = CareerMentorRAG()\n",
            "print('Career Mentor RAG initialized.')\n"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "query = 'How do I transition from software engineering into Machine Learning?'\n",
            "safe, reason = SafetyGuardrails.evaluate_input(query)\n",
            "print(f'Guardrail check: {\"SAFE\" if safe else f\"BLOCKED: {reason}\"}')\n",
            "\n",
            "if safe:\n",
            "    response = mentor.answer_question(query)\n",
            "    print('\\n--- Grounded Answer ---\\n', response.answer)\n",
            "    print('\\n--- Citations ---\\n', [c.document_title for c in response.citations])\n"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "unsupported_query = 'What is the exact internal travel reimbursement limit for Acme Widgets in 2029?'\n",
            "resp = mentor.answer_question(unsupported_query)\n",
            "print('Unsupported Query Answer:\\n', resp.answer)\n",
            "refused = any(term in resp.answer.lower() for term in [\"don't know\", 'not found', 'does not contain'])\n",
            "print('Strict refusal enforced:', refused)\n"
        ]
    }
]

with open(notebooks_dir / "03_rag_prototype.ipynb", "w", encoding="utf-8") as f:
    json.dump(create_nb(cells3), f, indent=2)

print("All 3 notebooks successfully written to notebooks/")
