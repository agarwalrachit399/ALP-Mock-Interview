from jinja2 import Environment, FileSystemLoader
from app.services.base.prompt_builder import PromptBuilder

env = Environment(loader=FileSystemLoader("app/services/prompts"))

class FollowupDecisionBuilder(PromptBuilder):
    def build(self, principle, time_remaining, num_principles_covered, history, time_spent, num_follow_up):
        template = env.get_template("followup_decision.j2")
        return template.render(
            principle=principle,
            time_remaining=time_remaining,
            num_principles_covered=num_principles_covered,
            num_follow_up=num_follow_up,
            time_spent=time_spent,
            history=history
        )
