import google.generativeai as genai
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def generate_story(prompt):
    """Generates a story based on the provided prompt."""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"An error occurred: {e}"

if __name__ == "__main__":
    print("Welcome to the AI Story Generator!")
    genre = input("Enter a genre (e.g., Sci-Fi, Fantasy, Mystery): ")
    characters = input("Enter the main characters (e.g., Alice, a clever detective): ")
    setting = input("Enter the setting (e.g., A futuristic city on Mars): ")
    
    full_prompt = (
        f"Write a creative and engaging short story in the {genre} genre. "
        f"The main characters are: {characters}. "
        f"The story is set in: {setting}."
    )
    
    print("\nGenerating your story...\n")
    story = generate_story(full_prompt)
    print("--- Your Story ---")
    print(story)
