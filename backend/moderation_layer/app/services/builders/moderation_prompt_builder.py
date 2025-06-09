from .prompt_loader import render_prompt

def build_moderation_prompt(question: str, user_input: str) -> str:
    return render_prompt("moderation_prompt.j2", question=question, user_input=user_input)

