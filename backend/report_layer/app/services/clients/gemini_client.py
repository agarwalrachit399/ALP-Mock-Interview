import google.generativeai as genai
from app.core.config import settings
from app.services.base.llm_base import LLMClientBase


genai.configure(api_key=settings.GOOGLE_API_KEY)

class GeminiClient(LLMClientBase):
    def __init__(self):
        self.model = genai.GenerativeModel("gemini-2.0-flash")

    def generate(self, prompt: str, temperature: float = 0.3) -> str:
        try:
            response = self.model.generate_content(prompt, generation_config={"temperature": temperature})
            return response.text.strip()
        except Exception as e:
            return f"[Gemini Error] {str(e)}"

gemini_client = GeminiClient()
