# from app.models import ReportRequest, ReportResponse
import json
import os 
from typing import Optional, Dict
from llm_clients.gemini_client import gemini_llm
from dotenv import load_dotenv
load_dotenv()






def load_lp_conversation(lp_key: str, data_file='data.json') -> tuple[str, str]:
    """Load conversation text and LP type for a given LP key from the JSON file."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, data_file)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"{data_file} not found at {file_path}")

    with open(file_path, 'r') as f:
        data = json.load(f)

    lp_data = data['conversations'].get(lp_key)
    if not lp_data:
        raise ValueError(f"No conversation found for LP '{lp_key}'")

    lp_type = lp_data.get("lp_type", "unknown")
    conversation = lp_data.get("conversation", [])

    lines = [f"{msg['role']}: {msg['content']}" for msg in conversation]
    conversation_text = "\n".join(lines)

    return conversation_text, lp_type
# print(load_lp_conversation("lp1"))

# -------------------------------
# 2. Build Prompt
# -------------------------------
def build_prompt(conversation_text: str, lp_type: str) -> str:
    return f"""
You are an expert Amazon behavioral interview evaluator.

Below is a conversation between an interviewer and a interviewee around a specific Amazon Leadership Principle (LP). Your task is to analyze the candidate's response deeply and provide structured evaluation.

Instructions:

1. Identify the **main Amazon Leadership Principle** that is demonstrated most strongly by the user. Confirm whether it aligns with the declared LP_type: "{lp_type}".
2. List any **secondary Leadership Principles** that are indirectly or partially demonstrated.
3. Provide a **score from 1 to 10** based on the following rubric:
   - STAR Format clearly followed → 3 points
   - Story is precise and focused → 1 point
   - Response is not verbose or rambling → 1 point
   - Story is highly relevant to the initial question → 3 points
   - Follow-up answers sound natural and realistic, not made up → 2 points
   -State where the marks were deducted

4. End your response with **2 concise lines describing areas of improvement** for the candidate to better reflect Amazon’s expectations.

Only use bullet points and short paragraphs for clarity. Format your response clearly under the following headings:
- Main LP Detected
- Secondary LPs Detected
- Score (out of 10)
- Areas for Improvement

Here is the conversation:

{conversation_text}
""".strip()



# -------------------------------
# 3. LLM API Wrapper (Pluggable)
# -------------------------------
def call_llm_api(prompt: str, llm_client) -> str:
    """
    Sends the prompt to a large language model via a client wrapper.
    Args:
        prompt (str): Full prompt string.
        llm_client (callable): Your LLM wrapper that accepts a prompt and returns response.
    Returns:
        str: Response from the model.
    """
    return llm_client(prompt)


# -------------------------------
# Optional: Direct Function to Run One LP
# -------------------------------
def analyze_lp(lp_key: str, llm_client, data_file='data.json') -> str:
    """High-level function to process one LP and get feedback."""
    conversation_text, lp_type = load_lp_conversation(lp_key, data_file)
    
    prompt = build_prompt(conversation_text, lp_type)
    return call_llm_api(prompt, gemini_llm)






# Now you can call analyze_lp with Gemini
if __name__ == "__main__":
    lp_key = "lp1"  # Example key
    response = analyze_lp(lp_key=lp_key, llm_client=gemini_llm, data_file='data.json')
    print(response)


