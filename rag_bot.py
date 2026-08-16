import google.generativeai as genai
import os

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-pro')

def get_rag_answer(query, context):
    prompt = f"Answer the following question using only the provided context. If the answer is not in the context, say you do not know.\n\nContext:\n{context}\n\nQuestion:\n{query}"
    response = model.generate_content(prompt)
    return response.text

if __name__ == "__main__":
    context = input("Enter the knowledge base context: ")
    query = input("Enter your question: ")
    print(get_rag_answer(query, context))
