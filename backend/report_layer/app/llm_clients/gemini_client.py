from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
load_dotenv()
# Initialize your Gemini API key once
API_KEY = os.getenv("GEMINI_API_KEY")  # or set it directly here (not recommended)
client = genai.Client(api_key=API_KEY )

def gemini_llm(prompt: str) -> str:
    """Call Gemini LLM with given prompt."""
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        # config=types.GenerateContentConfig(
        #     system_instruction="You are a cat. Your name is Neko."),
        contents=prompt
    )

    # Return the generated text
    return response.text
