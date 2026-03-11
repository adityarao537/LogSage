import requests
import json

API_URL = "http://localhost:5000"

def test_ingest():
    logs = [{
        "timestamp": "2023-10-27T10:00:00Z",
        "service": "test-service",
        "component": "test-component",
        "level": "INFO",
        "message": "Test log message"
    }]
    try:
        print(f"Sending POST to {API_URL}/ingest...")
        res = requests.post(f"{API_URL}/ingest", json=logs)
        print(f"Status: {res.status_code}")
        print(f"Response: {res.text}")
    except Exception as e:
        print(f"Ingest failed: {e}")

def test_logs():
    try:
        print(f"Sending GET to {API_URL}/logs...")
        res = requests.get(f"{API_URL}/logs")
        print(f"Status: {res.status_code}")
        print(f"Response: {res.text}")
    except Exception as e:
        print(f"Get Logs failed: {e}")

if __name__ == "__main__":
    test_ingest()
    test_logs()
