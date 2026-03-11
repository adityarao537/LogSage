# LogSage Backend

Python backend for log ingestion, normalization, and anomaly detection.

## Getting Started
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```
- Run main service:
  ```bash
  python main.py
  ```

## API Endpoints

- `POST /ingest` – Ingest a log entry (JSON)
  - Example:
    ```json
    {
      "timestamp": "2025-07-30T10:00:00Z",
      "service": "booking-api",
      "component": "db",
      "level": "ERROR",
      "message": "DB timeout error"
    }
    ```

- `GET /anomaly` – Returns detected anomalies from ingested logs
  - Example response:
    ```json
    {
      "anomaly": true,
      "count": 1,
      "details": "Anomalies detected.",
      "anomalies": [ ... ]
    }
    ```

## Testing

Run the test script to ingest sample logs and check for anomalies:
```bash
python test_api.py
```

## Tech Stack
- Python
- Logstash, AWS SDKs
- ML: scikit-learn, Prophet, PyOD
