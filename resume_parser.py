from google import genai
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

def parse_resume(resume_text):
    prompt = f"Extract the following information from the resume:\n- Name\n- Email\n- Phone\n- Skills\n- Experience (brief summary)\n\nResume text:\n{resume_text}"
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents=prompt
    )
    return response.text

if __name__ == "__main__":
    resume_text = input("Enter the raw text of the resume: ")
    print(parse_resume(resume_text))
