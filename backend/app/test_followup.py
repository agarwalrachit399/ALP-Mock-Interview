import requests
import json
import uuid

BASE_URL = "http://localhost:8000"

def test_followup_generation():
    """Test the followup generation functionality"""
    print("Testing Followup Generation Service...\n")
    
    # Generate a unique session ID for testing
    session_id = str(uuid.uuid4())
    principle = "Customer Obsession"
    
    # Test 1: Generate initial followup
    print("Test 1: Generate Initial Followup")
    request_data = {
        "session_id": session_id,
        "principle": principle,
        "question": "Tell me about a time you went above and beyond for a customer.",
        "user_input": "I once worked late to fix a customer's urgent issue. We had a client whose system went down right before their important presentation."
    }
    
    try:
        response = requests.post(f"{BASE_URL}/followup/generate-followup", json=request_data)
        if response.status_code == 200:
            result = response.json()
            followup_question = result["followup"]
            print(f"✅ Generated followup: {followup_question}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return
    except Exception as e:
        print(f"❌ Exception: {e}")
        return

    # Test 2: Check if should generate another followup
    print("\nTest 2: Should Generate Decision")
    should_generate_data = {
        "session_id": session_id,
        "principle": principle,
        "question": followup_question,
        "user_input": "I stayed until 2 AM debugging the issue and coordinated with our backend team to implement a fix.",
        "time_remaining": 15,
        "time_spent": 5,
        "num_followups": 1,
        "num_lp_questions": 1
    }
    
    try:
        response = requests.post(f"{BASE_URL}/followup/should-followup", json=should_generate_data)
        if response.status_code == 200:
            result = response.json()
            should_followup = result["followup"]
            print(f"✅ Should generate followup: {should_followup}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return
    except Exception as e:
        print(f"❌ Exception: {e}")
        return

    # Test 3: Generate another followup if recommended
    if should_followup:
        print("\nTest 3: Generate Second Followup")
        request_data["question"] = followup_question
        request_data["user_input"] = should_generate_data["user_input"]
        
        try:
            response = requests.post(f"{BASE_URL}/followup/generate-followup", json=request_data)
            if response.status_code == 200:
                result = response.json()
                second_followup = result["followup"]
                print(f"✅ Generated second followup: {second_followup}")
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Exception: {e}")

    # Test 4: Check memory stats
    print("\nTest 4: Memory Statistics")
    try:
        response = requests.get(f"{BASE_URL}/followup/memory-stats")
        if response.status_code == 200:
            result = response.json()
            stats = result["stats"]
            print(f"✅ Memory stats:")
            print(f"   - Total sessions: {stats['total_sessions']}")
            print(f"   - Total principles: {stats['total_principles']}")
            print(f"   - Total history entries: {stats['total_history_entries']}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Exception: {e}")

    # Test 5: Get session details
    print("\nTest 5: Session Details")
    try:
        response = requests.get(f"{BASE_URL}/followup/session-details/{session_id}")
        if response.status_code == 200:
            result = response.json()
            if result["success"]:
                details = result["details"]
                print(f"✅ Session details:")
                print(f"   - Session ID: {details['session_id']}")
                print(f"   - Total principles: {details['total_principles']}")
                for principle, data in details['principles'].items():
                    print(f"   - {principle}: {data['history_length']} history entries")
            else:
                print(f"❌ Session not found: {result['message']}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Exception: {e}")

    # Test 6: Cleanup session
    print("\nTest 6: Session Cleanup")
    try:
        cleanup_data = {"session_id": session_id}
        response = requests.post(f"{BASE_URL}/followup/cleanup-session", json=cleanup_data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Cleanup result: {result['message']}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Exception: {e}")

    print("\n🎉 Followup generation testing complete!")

if __name__ == "__main__":
    test_followup_generation()