import requests
import json

BASE_URL = "http://localhost:8000"

def test_auth():
    # Test signup
    signup_data = {
        "name": "Test User",
        "email": "agarwalrachit399@gmail.com", 
        "password": "password123"
    }
    
    print("Testing signup...")
    signup_response = requests.post(f"{BASE_URL}/auth/signup", json=signup_data)
    print(f"Signup Status: {signup_response.status_code}")
    
    if signup_response.status_code == 200:
        result = signup_response.json()

        print(f"Signup Success: {result['name']} ({result['email']})")
        
        # Test login
        login_data = {
            "email": "agarwalrachit399@gmail.com",
            "password": "password123"
        }
        
        print("\nTesting login...")
        login_response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        print(f"Login Status: {login_response.status_code}")
        
        if login_response.status_code == 200:
            login_result = login_response.json()
            print(f"Login Success! Token: {login_result['token'][:20]}...")
        else:
            print(f"Login Failed: {login_response.text}")
    else:
        print(f"Signup Failed: {signup_response.text}")

if __name__ == "__main__":
    test_auth()