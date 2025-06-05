from fastapi.testclient import TestClient
from llm_microservice import app

client = TestClient(app)

# Mock session 1 - Initial LP question
initial_payload = {
    "session_id": "test_sess_001",
    "principle": "Customer Obsession",
    "question": "Tell me about a time you went above and beyond for a customer.",
    "user_input": "A customer reached out right before closing time with a major issue placing an urgent order. I stayed 2 extra hours, coordinated with our logistics team, and ensured the package was dispatched that night."
}

# Mock session 1 - Follow-up 1
followup_1 = {
    "session_id": "test_sess_001",
    "principle": "Customer Obsession",
    "question": "What motivated you to go the extra mile?",
    "user_input": "I empathized with their situation — they had a wedding the next day and needed the item urgently. I knew how much it meant to them."
}

# Mock session 1 - Follow-up 2
followup_2 = {
    "session_id": "test_sess_001",
    "principle": "Customer Obsession",
    "question": "How did the customer respond?",
    "user_input": "They were incredibly grateful, sent a thank-you letter to my manager, and even posted a positive review praising our customer service."
}

def test_llm_microservice_initial():
    response = client.post("/generate-followup", json=initial_payload)
    print(response.json())
    assert response.status_code == 200
    assert "followup_question" in response.json()

def test_llm_microservice_followup_1():
    response = client.post("/generate-followup", json=followup_1)
    print(response.json())
    assert response.status_code == 200
    assert "followup_question" in response.json()

# def test_llm_microservice_followup_2():
#     response = client.post("/generate-followup", json=followup_2)
#     assert response.status_code == 200
#     assert "followup_question" in response.json()
test_llm_microservice_initial()
test_llm_microservice_followup_1()