from jinja2 import Environment, FileSystemLoader
from app.services.base.prompt_builder import PromptBuilder

env = Environment(loader=FileSystemLoader("app/services/prompts"))

class FollowupQuestionBuilder(PromptBuilder):
    def build(self, principle, history):
        template = env.get_template("followup_question.j2")
        return template.render(principle=principle, history=history)
