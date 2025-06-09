import os
from jinja2 import Environment, FileSystemLoader, select_autoescape

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")

env = Environment(
    loader=FileSystemLoader(PROMPT_DIR),
    autoescape=select_autoescape(enabled_extensions=('j2',))
)

def render_prompt(template_name: str, **kwargs) -> str:
    template = env.get_template(template_name)
    return template.render(**kwargs)
