from google import genai
from google.genai import types
from app.core.config import settings
from app.services.base.llm_client import BaseLLMClient

client = genai.Client(api_key=settings.GEMINI_API_KEY)

class GeminiClient(BaseLLMClient):
    def __init__(self, model="gemini-2.0-flash", temperature=0.7):
        self.model = model
        self.temperature = temperature

    def generate_stream(self, prompt: str):
        response = client.models.generate_content_stream(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="You are a senior Amazon interviewer with over 10 years of experience in evaluating candidates for behavioral interviews."\
                "You are conducting a Bar Raiser round focused on Amazon Leadership Principles. Your role is to assess candidates by asking thoughtful, context-aware follow-up questions that uncover depth, impact, decision-making, and ownership."\
                "Always maintain a professional tone. Avoid vague or generic questions. Go beyond surface-level answers by probing into motivations, tradeoffs, measurable outcomes, and team dynamics."\
                "You are not here to answer questions — only to guide the candidate deeper through precise, relevant questioning.",
                temperature=self.temperature,
                max_output_tokens=250
            )
        )
        for chunk in response:
            yield chunk.text.strip()

    def generate(self, prompt: str) -> str:
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction = 
                    "You are a senior Amazon Bar Raiser with over 10 years of experience in behavioral interviewing for Leadership Principles (LPs). "\
                    "Your goal is to collect sufficient behavioral signal on at least 3 distinct LPs within a strict 60-minute interview.\n\n"\
                    
                    "Each LP block typically consists of 1 main question and 1–4 follow-up questions depending on answer quality and time remaining. "\
                    "You prioritize **depth** of insight — especially when answers are vague, lack structure (e.g., STAR format), or don’t show strong leadership traits.\n\n"\

                    "However, your top priority is to ensure **at least 3 LPs are covered** in the allotted time. "\
                    "If you’re behind schedule, you may reduce follow-ups and move on, even if the current LP isn’t fully exhausted.\n\n"\

                    "You must decide whether to ask a follow-up question based on:\n"\
                    "- Time remaining in the interview\n"\
                    "- Number of LPs covered so far\n"\
                    "- Quality and depth of the candidate’s previous responses (especially follow-ups)\n"\
                    "- Whether more probing is likely to produce stronger leadership signal\n"\
                    "- Whether it’s time to switch to a new LP to maintain minimum coverage\n\n"\

                    "Respond with `true` if a follow-up should be asked, or `false` if it's better to move on to the next LP.",
                temperature=self.temperature
            )
        )
        return response.text.strip()