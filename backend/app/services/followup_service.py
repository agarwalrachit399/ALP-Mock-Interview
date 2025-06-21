from google import genai
from google.genai import types
from jinja2 import Environment, FileSystemLoader
import os
from app.core.config import settings
from app.services.session_memory import session_memory_manager
from app.models.followup import FollowupRequest, ShouldGenerateRequest

# Setup Jinja2 environment for templates
template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
env = Environment(loader=FileSystemLoader(template_dir))

class GeminiClient:
    def __init__(self, model="gemini-2.0-flash", temperature=0.7):
        self.model = model
        self.temperature = temperature
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    def generate_stream(self, prompt: str) -> str:
        """Generate followup question"""
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="You are a senior Amazon interviewer with over 10 years of experience in evaluating candidates for behavioral interviews."
                "You are conducting a Bar Raiser round focused on Amazon Leadership Principles. Your role is to assess candidates by asking thoughtful, context-aware follow-up questions that uncover depth, impact, decision-making, and ownership."
                "Always maintain a professional tone. Avoid vague or generic questions. Go beyond surface-level answers by probing into motivations, tradeoffs, measurable outcomes, and team dynamics."
                "You are not here to answer questions — only to guide the candidate deeper through precise, relevant questioning.",
                temperature=self.temperature,
                max_output_tokens=250
            )
        )
        return response.text.strip()

    def generate_decision(self, prompt: str) -> str:
        """Generate followup decision"""
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction = 
                    "You are a senior Amazon Bar Raiser with over 10 years of experience in behavioral interviewing for Leadership Principles (LPs). "
                    "Your goal is to collect sufficient behavioral signal on at least 2 distinct LPs within a strict 30-minute interview.\n\n"
                    
                    "Each LP block typically consists of 1 main question and 1–4 follow-up questions depending on answer quality and time remaining. "
                    "You prioritize **depth** of insight — especially when answers are vague, lack structure (e.g., STAR format), or don't show strong leadership traits.\n\n"

                    "However, your top priority is to ensure **at least 2 LPs are covered** in the allotted time. "
                    "If you're behind schedule, you may reduce follow-ups and move on, even if the current LP isn't fully exhausted.\n\n"

                    "You must decide whether to ask a follow-up question based on:\n"
                    "- Time remaining in the interview\n"
                    "- Number of LPs covered so far\n"
                    "- Quality and depth of the candidate's previous responses (especially follow-ups)\n"
                    "- Whether more probing is likely to produce stronger leadership signal\n"
                    "- Whether it's time to switch to a new LP to maintain minimum coverage\n\n"

                    "Respond with `true` if a follow-up should be asked, or `false` if it's better to move on to the next LP.",
                temperature=self.temperature
            )
        )
        return response.text

class FollowupService:
    def __init__(self):
        self.question_client = GeminiClient(temperature=0.7)
        self.decision_client = GeminiClient(temperature=0.2)

    def _build_followup_question_prompt(self, principle: str, history: list) -> str:
        """Build prompt for followup question generation"""
        template = env.get_template("followup_question.j2")
        return template.render(principle=principle, history=history)

    def _build_followup_decision_prompt(self, principle: str, time_remaining: int, 
                                       num_principles_covered: int, history: list, 
                                       time_spent: int, num_follow_up: int) -> str:
        """Build prompt for followup decision"""
        template = env.get_template("followup_decision.j2")
        return template.render(
            principle=principle,
            time_remaining=time_remaining,
            num_principles_covered=num_principles_covered,
            num_follow_up=num_follow_up,
            time_spent=time_spent,
            history=history
        )

    def generate_followup(self, request: FollowupRequest) -> str:
        """Generate a followup question"""
        session_id, principle, question, user_input = (
            request.session_id, request.principle, request.question, request.user_input
        )

        # Update session memory
        if not session_memory_manager.has_session(session_id, principle):
            session_memory_manager.start_lp(session_id, principle, question, user_input)
        else:
            session_memory_manager.add_followup(session_id, principle, question, user_input)

        # Get conversation history
        history = session_memory_manager.get_history(session_id, principle)
        
        # Generate followup question
        prompt = self._build_followup_question_prompt(principle, history)
        followup = self.question_client.generate_stream(prompt)
        
        return followup

    def should_generate_followup(self, request: ShouldGenerateRequest) -> bool:
        """Decide whether to generate a followup question"""
        # Update session memory
        if not session_memory_manager.has_session(request.session_id, request.principle):
            session_memory_manager.start_lp(request.session_id, request.principle, 
                                           request.question, request.user_input)
        else:
            session_memory_manager.add_followup(request.session_id, request.principle, 
                                               request.question, request.user_input)

        # Get conversation history
        history = session_memory_manager.get_history(request.session_id, request.principle)
        
        # Generate decision
        prompt = self._build_followup_decision_prompt(
            request.principle,
            request.time_remaining,
            request.num_lp_questions,
            history,
            request.time_spent,
            request.num_followups
        )
        
        result = self.decision_client.generate_decision(prompt).lower()
        
        if "true" in result:
            return True
        elif "false" in result:
            return False
        else:
            print(f"⚠️ Unexpected followup decision response: {result}")
            return True  # Default to generating followup

# Global followup service instance
followup_service = FollowupService()