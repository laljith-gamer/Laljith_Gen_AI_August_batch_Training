# !pip install -q -U google-genai faiss-cpu

import numpy as np
import faiss

from google import genai
from google.genai import types
import os


# Connect to Gemini
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEYS")
)

MODEL = "gemini-embedding-001"


# Convert text into an embedding vector
def embed(text):
    response = client.models.embed_content(
        model=MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            output_dimensionality=768
        )
    )

    return response.embeddings[0].values


# Candidate data
candidates = [
    "React developer with payment experience",
    "Cardiologist with 12 years experience",
    "Backend engineer with Kubernetes and Go",
    "iOS developer using Swift",
    "MBBS doctor in internal medicine",
    "DevOps engineer with AWS and Terraform"
]


# Convert all candidates into vectors
vectors = np.array([
    embed(candidate)
    for candidate in candidates
])

print("Number of candidates:", len(candidates))
print("Vector shape:", vectors.shape)


# Normalize vectors
vectors = vectors / np.linalg.norm(
    vectors,
    axis=1,
    keepdims=True
)


# Cosine similarity
query = "React developer with payment gateway experience"

query_vector = np.array(embed(query))

# Normalize query vector
query_vector = query_vector / np.linalg.norm(query_vector)

# Calculate similarity scores
scores = np.dot(vectors, query_vector)

# Get top 3 matches
top_indices = np.argsort(scores)[::-1][:3]


print("\nQuery:", query)
print("\nTop Matches:")

for i in top_indices:
    print(f"{scores[i]:.3f} → {candidates[i]}")


# Create FAISS index
dimension = vectors.shape[1]

index = faiss.IndexFlatIP(dimension)

# Add vectors to FAISS
index.add(vectors.astype("float32"))

print("\nFAISS index created!")
print("Vectors stored:", index.ntotal)


# Search using FAISS
query = "Cloud engineer with AWS experience"

query_vector = np.array(
    embed(query),
    dtype="float32"
)

# Normalize query
query_vector = query_vector / np.linalg.norm(query_vector)

# FAISS expects a 2D array
query_vector = query_vector.reshape(1, -1)

# Search for top 3 matches
scores, indices = index.search(
    query_vector,
    3
)


print("\nQuery:", query)
print("\nFAISS Results:")

for score, i in zip(scores[0], indices[0]):
    print(f"{score:.3f} → {candidates[i]}")
