import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test_flow():
    print("Testing LogSage API Flow...")
    
    # 1. Ingest Logs
    logs = [
        {
            "timestamp": "2025-07-30T10:00:00Z",
            "service": "booking-api",
            "component": "db",
            "level": "INFO",
            "message": "Connection established"
        },
        {
            "timestamp": "2025-07-30T10:00:01Z",
            "service": "payment-gateway",
            "component": "api",
            "level": "ERROR",
            "message": "Timeout waiting for bank response"
        }
    ]
    
    print(f"Ingesting {len(logs)} logs...")
    try:
        res = requests.post(f"{BASE_URL}/ingest", json=logs)
        print(f"Ingest Status: {res.status_code}")
        assert res.status_code == 201
    except Exception as e:
        print(f"Ingest failed: {e}")
        return

    # 2. Get Logs
    print("Fetching logs...")
    try:
        res = requests.get(f"{BASE_URL}/logs")
        fetched_logs = res.json()
        print(f"Fetched {len(fetched_logs)} logs.")
        assert len(fetched_logs) >= 2
    except Exception as e:
        print(f"Get Logs failed: {e}")
        return

    # 3. Check Anomalies
    print("Checking anomalies...")
    try:
        res = requests.get(f"{BASE_URL}/anomaly")
        anomalies = res.json()
        print(f"Anomaly Response: {anomalies}")
    except Exception as e:
        print(f"Anomaly check failed: {e}")
        return

    print("Flow Test Completed Successfully.")

if __name__ == "__main__":
    test_flow()
