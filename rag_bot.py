from google import genai
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

if not os.getenv("GEMINI_API_KEY"):
    raise RuntimeError("GEMINI_API_KEY is missing. Add it to the project .env file.")

client = genai.Client()

def get_rag_answer(query, context):
    prompt = f"Answer the following question using only the provided context. If the answer is not in the context, say you do not know.\n\nContext:\n{context}\n\nQuestion:\n{query}"
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text

if __name__ == "__main__":
    context = input("Enter the knowledge base context: ")
    query = input("Enter your question: ")
    print(get_rag_answer(query, context))
