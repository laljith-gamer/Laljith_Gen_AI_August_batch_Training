import google.generativeai as genai
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def generate_social_media_post(topic, platform):
    prompt = f"Generate a creative social media post for {platform} about {topic}. Include relevant hashtags."
    response = model.generate_content(prompt)
    return response.text

if __name__ == "__main__":
    topic = input("Enter the topic: ")
    platform = input("Enter the platform (e.g., Twitter, LinkedIn, Instagram): ")
    print(generate_social_media_post(topic, platform))
