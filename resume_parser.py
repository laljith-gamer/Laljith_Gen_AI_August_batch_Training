from google import genai
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

if not os.getenv("GEMINI_API_KEY"):
    raise RuntimeError("GEMINI_API_KEY is missing. Add it to the project .env file.")

client = genai.Client()

def parse_resume(resume_text):
    prompt = f"Extract the following information from the resume:\n- Name\n- Email\n- Phone\n- Skills\n- Experience (brief summary)\n\nResume text:\n{resume_text}"
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text

if __name__ == "__main__":
    resume_text = input("Enter the raw text of the resume: ")
    print(parse_resume(resume_text))
