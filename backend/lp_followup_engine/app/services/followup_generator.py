from app.services.clients.gemini_client import GeminiClient
from app.services.builders.followup_question_builder import FollowupQuestionBuilder

class FollowupGenerator:
    def __init__(self, llm_client=None, prompt_builder=None):
        self.llm_client = llm_client or GeminiClient()
        self.prompt_builder = prompt_builder or FollowupQuestionBuilder()

    def generate(self, principle, history):
        prompt = self.prompt_builder.build(principle=principle, history=history)
        return self.llm_client.generate_stream(prompt)