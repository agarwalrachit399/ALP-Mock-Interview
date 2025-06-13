
import google.generativeai as genai
from app.core.config import settings
from app.services.base.llm_base import LLMClientBase
from app.schemas.schema import ReportResponse
from guardrails import Guard
from jinja2 import Template
import logging


genai.configure(api_key=settings.GEMINI_API_KEY)

_gemini_model = genai.GenerativeModel("gemini-2.0-flash")

guard=Guard.for_pydantic(ReportResponse)

with open("app/services/prompts/analyze_lp.j2", "r") as f:
    prompt_template = Template(f.read())

class GeminiClient(LLMClientBase):
    def __init__(self):
        
        self.model = _gemini_model 

    def generate(self, prompt: str, temperature: float = 0.1) -> ReportResponse | str:
        try: 
            result = guard(
                messages=[{"role":"user", "content":prompt}],
                model="gemini/gemini-2.0-flash",
                temperature=temperature,
                max_tokens=5000 
                )

            return result.validated_output
        except Exception as e:
            logging.exception("Guardrails validation failed.")
            return f"[Gemini Error] {str(e)}"

    def generate_with_conversation(self, conversation: list[str], intended_lp: str) -> ReportResponse | str:
        try:
            prompt_text = prompt_template.render(
                conversation_text="\n".join(conversation),
                # lp_type=intended_lp
            )
            
            return self.generate(prompt_text)
        except Exception as e:
            logging.exception("Prompt generation failed.")
            return f"[Prompt Error] {str(e)}"

gemini_client = GeminiClient()