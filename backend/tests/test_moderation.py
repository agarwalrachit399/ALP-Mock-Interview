import requests
import json

BASE_URL = "http://localhost:8000"

def test_moderation():
    test_cases = [
        {
            "name": "Safe answer",
            "question": "Tell me about a time you showed leadership",
            "user_input": "I led a team project where we had to deliver a mobile app in 3 months. I organized daily standups and helped resolve conflicts.",
            "expected": "safe"
        },
        {
            "name": "Off-topic response", 
            "question": "Tell me about a time you showed leadership",
            "user_input": "What's the weather like today?",
            "expected": "off_topic"
        },
        {
            "name": "Repeat request",
            "question": "Tell me about a time you showed leadership", 
            "user_input": "Can you repeat the question?",
            "expected": "repeat"
        },
        {
            "name": "Change request",
            "question": "Tell me about a time you showed leadership",
            "user_input": "Can we change this question to something else?", 
            "expected": "change"
        },
        {
            "name": "Thinking response",
            "question": "Tell me about a time you showed leadership",
            "user_input": "Let me think about this for a moment",
            "expected": "thinking"
        }
    ]
    
    print("Testing Moderation Service...\n")
    
    for test_case in test_cases:
        print(f"Testing: {test_case['name']}")
        
        payload = {
            "question": test_case["question"],
            "user_input": test_case["user_input"]
        }
        
        try:
            response = requests.post(f"{BASE_URL}/moderation/moderate", json=payload)
            
            if response.status_code == 200:
                result = response.json()
                status = result["status"]
                print(f"  Input: {test_case['user_input'][:50]}...")
                print(f"  Result: {status}")
                print(f"  Expected: {test_case['expected']}")
                print(f"  ✅ Success" if status == test_case['expected'] else f"  ⚠️  Different result")
            else:
                print(f"  ❌ Error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"  ❌ Exception: {e}")
            
        print()

if __name__ == "__main__":
    test_moderation()