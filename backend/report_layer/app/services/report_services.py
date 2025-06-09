from typing import List, Dict, Any
from app.services.clients.gemini_client import gemini_client
from app.services.builders.prompt_builder import render_prompt
from app.db.db_handler import get_all_conversations_by_session

def analyze_lp_from_doc(doc: Dict[str, Any]) -> str:
    lp_type = doc.get("principle", "unknown")

    conversation = []
    mq = doc.get("main_question", {})
    conversation.append(f"Interviewer: {mq.get('question', '')}")
    conversation.append(f"Candidate: {mq.get('answer', '')}")

    for fup in doc.get("followups", []):
        conversation.append(f"Interviewer: {fup.get('question', '')}")
        conversation.append(f"Candidate: {fup.get('answer', '')}")

    conversation_text = "\n".join(conversation)

    prompt = render_prompt(
        "analyze_lp.j2",
        lp_type=lp_type,
        conversation_text=conversation_text
    )

    return gemini_client.generate(prompt)

def analyze_all_principles_for_session(session_id: str) -> List[Dict[str, Any]]:
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
