from google import genai
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

def get_rag_answer(query, context):
    prompt = f"Answer the following question using only the provided context. If the answer is not in the context, say you do not know.\n\nContext:\n{context}\n\nQuestion:\n{query}"
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents=prompt
    )
    return response.text

if __name__ == "__main__":
    context = input("Enter the knowledge base context: ")
    query = input("Enter your question: ")
    print(get_rag_answer(query, context))
