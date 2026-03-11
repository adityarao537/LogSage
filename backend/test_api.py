import requests

BASE_URL = "http://localhost:5000"

sample_logs = [
    {"timestamp": "2025-07-30T10:00:00Z", "service": "booking-api", "component": "db", "level": "ERROR", "message": "DB timeout error"},
    {"timestamp": "2025-07-30T10:01:00Z", "service": "inventory-service", "component": "cache", "level": "WARN", "message": "Cache miss"},
    {"timestamp": "2025-07-30T10:02:00Z", "service": "payment-gateway", "component": "gateway", "level": "ERROR", "message": "Stripe 503 error"},
    {"timestamp": "2025-07-30T10:03:00Z", "service": "booking-api", "component": "api", "level": "INFO", "message": "Request received"},
    {"timestamp": "2025-07-30T10:04:00Z", "service": "inventory-service", "component": "db", "level": "ERROR", "message": "DB connection lost"},
    {"timestamp": "2025-07-30T10:05:00Z", "service": "payment-gateway", "component": "api", "level": "INFO", "message": "Payment processed"}
]

def ingest_logs():
    for log in sample_logs:
        resp = requests.post(f"{BASE_URL}/ingest", json=log)
        print(f"Ingest: {resp.status_code} {resp.json()}")

def check_anomaly():
    resp = requests.get(f"{BASE_URL}/anomaly")
    print(f"Anomaly: {resp.status_code} {resp.json()}")

if __name__ == "__main__":
    ingest_logs()
    check_anomaly()
