from .llm_clients.gemini_client import gemini_llm
from .db_handler import get_all_conversations_by_session  

def call_llm_api(prompt: str, llm_client) -> str:
    return llm_client(prompt)


def build_prompt(conversation_text: str, lp_type: str) -> str:
    return f"""
        You are an expert who has 15 years of  working experience at Amazon and your task is to evalute a candiate critically to make sure only the best and genuine is hired at Amazon so evaluate accordingly.

        Below is a conversation between an interviewer and a interviewee around a specific Amazon Leadership Principle (LP). Your task is to analyze the candidate's response deeply and provide structured evaluation.

        Instructions:

        1. Identify the main Amazon Leadership Principle that is demonstrated most strongly by the user. Confirm whether it aligns with the declared LP type: "{lp_type}".
        2. List any secondary Leadership Principles that are indirectly or partially demonstrated.
        3. Provide a score from 1 to 10 based on the following rubric:
        - STAR Format clearly followed → 3 points
        - Story is precise and focused → 1 point
        - Response is not verbose or rambling → 1 point
        - Story is highly relevant to the initial question → 3 points
        - Follow-up answers sound natural and realistic, not made up → 2 points
        4.State where the marks were deducted.

        4. End your response with one para describing areas of improvement for the candidate to better reflect Amazon’s expectations.
        5. Dont bold anything
        Only use bullet points and short paragraphs for clarity. Format your response clearly under the following headings:
        - Main LP Detected
        - Secondary LPs Detected
        - Score (out of 10)
        - Areas for Improvement(Descriptive)

        Here is the conversation:

        {conversation_text}
        """.strip()

def analyze_lp_from_doc(doc: dict) -> str:
    lp_type = doc.get("principle", "unknown")

    conversation = []
    mq = doc.get("main_question", {})
    conversation.append(f"Interviewer: {mq.get('question', '')}")
    conversation.append(f"Candidate: {mq.get('answer', '')}")

    for fup in doc.get("followups", []):
        conversation.append(f"Interviewer: {fup.get('question', '')}")
        conversation.append(f"Candidate: {fup.get('answer', '')}")

    conversation_text = "\n".join(conversation)
    print(conversation_text)
    prompt = build_prompt(conversation_text, lp_type)
    return call_llm_api(prompt, gemini_llm)


def analyze_all_principles_for_session(session_id: str):
    docs = get_all_conversations_by_session(session_id)
    results = []

    for doc in docs:
        try:
            result = analyze_lp_from_doc(doc)
            results.append({
                "principle": doc.get("principle"),
                "analysis": result
            })
        except Exception as e:
            results.append({
                "principle": doc.get("principle"),
                "error": str(e)
            })

    return results  

