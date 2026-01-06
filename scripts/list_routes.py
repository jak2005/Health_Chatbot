import requests
import json

API_URL = "http://localhost:8080"

try:
    response = requests.get(f"{API_URL}/openapi.json")
    if response.status_code == 200:
        data = response.json()
        paths = data.get("paths", {}).keys()
        print("Available paths:")
        for path in sorted(paths):
            print(f"  - {path}")
    else:
        print(f"Failed to get openapi.json: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")
