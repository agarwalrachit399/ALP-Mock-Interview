from app.services.base.moderation_model import GeminiModerationClient
from app.services.builders.moderation_prompt_builder import build_moderation_prompt
from app.schemas.moderation import ModerationResponse

class Moderator:
    def __init__(self):
        self.client = GeminiModerationClient()

    def moderate(self, question: str, user_input: str) -> ModerationResponse:
        prompt = build_moderation_prompt(question, user_input)
        classification = self.client.generate(prompt).strip().lower()
        print(f"[MODERATION] Classification: {classification}")

        valid_labels = {"abusive", "off_topic", "malicious", "repeat", "change", "thinking"}
        return ModerationResponse(status=classification if classification in valid_labels else "safe")
