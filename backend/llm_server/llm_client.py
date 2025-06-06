import os
from jinja2 import Template
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize the Gemini API client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)


class PromptBuilder:
    TEMPLATE = Template("""
You are currently interviewing a candidate for the Amazon Leadership Principle: **{{ principle }}**.

Below is the conversation so far between you (the interviewer) and the candidate:

{% for msg in history %}
{{ msg.role|capitalize }}: {{ msg.content }}
{% endfor %}

Based on this conversation, ask ONE thoughtful and targeted follow-up question that helps you evaluate the candidate’s depth in the Leadership Principle: **{{ principle }}**.

Your follow-up should do one or more of the following:
- Clarify any ambiguous or vague parts of the candidate's response
- Explore their motivations or decision-making process
- Probe for measurable outcomes or impact
- Understand trade-offs, challenges, or team dynamics

Avoid repeating previous questions. Keep your tone professional and curious.

Only return the next follow-up question. Do not add any commentary or explanation.
""")

    @staticmethod
    def build_prompt(principle, history):
        return PromptBuilder.TEMPLATE.render(principle=principle, history=history)

class LLMClient:
    def __init__(self, model="gemini-2.0-flash"):
        self.model = model

    def generate_followup(self, principle, history):
        prompt = PromptBuilder.build_prompt(principle, history)
        

        response = client.models.generate_content_stream(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="You are a senior Amazon interviewer with over 10 years of experience in evaluating candidates for behavioral interviews."\
                "You are conducting a Bar Raiser round focused on Amazon Leadership Principles. Your role is to assess candidates by asking thoughtful, context-aware follow-up questions that uncover depth, impact, decision-making, and ownership."\
                "Always maintain a professional tone. Avoid vague or generic questions. Go beyond surface-level answers by probing into motivations, tradeoffs, measurable outcomes, and team dynamics."\
                "You are not here to answer questions — only to guide the candidate deeper through precise, relevant questioning.",
                max_output_tokens=250,
                temperature=0.7) 
        )

        for chunk in response:
            yield chunk.text.strip()