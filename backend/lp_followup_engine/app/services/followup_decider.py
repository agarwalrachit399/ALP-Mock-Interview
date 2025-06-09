from app.services.clients.gemini_client import GeminiClient
from app.services.builders.followup_decision_builder import FollowupDecisionBuilder

class FollowupDecider:
    def __init__(self, llm_client=None, prompt_builder=None):
        self.llm_client = llm_client or GeminiClient(temperature=0.2)
        self.prompt_builder = prompt_builder or FollowupDecisionBuilder()

    def decide(self, principle, time_remaining, num_lp_covered, history, time_spent, num_follow_up):
        prompt = self.prompt_builder.build(
            principle=principle,
            time_remaining=time_remaining,
            num_principles_covered=num_lp_covered,
            history=history,
            time_spent=time_spent,
            num_follow_up=num_follow_up
        )
        result = self.llm_client.generate(prompt).lower()
        if "true" in result:
            return True
        elif "false" in result:
            return False
        raise ValueError(f"Unexpected response: {result}")