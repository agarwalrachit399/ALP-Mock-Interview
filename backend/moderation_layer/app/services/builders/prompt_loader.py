from jinja2 import Environment, FileSystemLoader
import os

PROMPT_DIR = os.path.join(os.path.dirname(__file__), '..', 'prompts')
env = Environment(loader=FileSystemLoader(PROMPT_DIR))

def render_prompt(template_name: str, **kwargs) -> str:
    template = env.get_template(template_name)
    return template.render(**kwargs)
