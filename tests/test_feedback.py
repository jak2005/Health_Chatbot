import requests
import json
import time

API_URL = "http://localhost:8080"

def test_feedback_flow():
    print(f"Testing API at {API_URL}")
    
    # 1. Submit Feedback
    feedback_payload = {
        "user_id": "test_user_123",
        "rating": 5,
        "comment": "This is a test feedback from Antigravity verification."
    }
    
    try:
        print("Submitting feedback...")
        response = requests.post(f"{API_URL}/feedback", json=feedback_payload)
        print(f"Submit Status: {response.status_code}")
        print(f"Submit Response: {response.json()}")
        
        if response.status_code != 200:
            print("FAILED: Submit feedback failed.")
            return

        # 2. Retrieve Feedback (as Admin)
        print("Retrieving admin feedback...")
        response = requests.get(f"{API_URL}/admin/feedback")
        print(f"Retrieve Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            feedbacks = data.get("feedback", [])
            print(f"Found {len(feedbacks)} feedback items.")
            
            # Verify our feedback is there
            found = False
            for f in feedbacks:
                if f.get("user_id") == "test_user_123" and f.get("rating") == 5:
                    print("SUCCESS: Verified recently submitted feedback exists in database.")
                    found = True
                    break
            
            if not found:
                print("FAILED: Submitted feedback not found in admin list.")
                print("List contents:", feedbacks)
        else:
            print(f"FAILED: Retrieve feedback failed. {response.text}")

    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_feedback_flow()
