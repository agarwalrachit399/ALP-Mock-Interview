import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

gemini_model = genai.GenerativeModel("gemini-pro")

def gemini_llm(prompt: str, temperature=0.3) -> str:
    try:
        response = gemini_model.generate_content(prompt, generation_config={"temperature": temperature})
        return response.text.strip()
    except Exception as e:
        return f"[Gemini Error] {str(e)}"
