# High Scale Architecture Guide

LogSage is designed to work alongside a high-volume ELK stack (5TB+ daily logs).

## 1. Handling 5TB of Logs
For high-volume ingestion, the heavy lifting is done by **Elasticsearch** and **Logstash/Beats**, not LogSage.

- **Ingestion**: Continue using your existing Logstash/Filebeat pipelines. Do **not** send 5TB of data through LogSage's `/ingest` endpoint, as that is for ad-hoc/testing only.
- **Analysis**: LogSage connects to Elasticsearch and queries **windowed data** (e.g., last 500 logs) for anomaly detection. This ensures the app remains fast regardless of total storage.
    - *Scalability Check*: Ensure your Elasticsearch cluster has sufficient Data Nodes to handle the 5TB indexing rate.

## 2. Scanning Multiple Indexes
To scan multiple indexes (e.g., `audit-logs-*` and `app-logs-*`):

1.  Set the environment variable:
    ```yaml
    - name: ES_INDEX_PATTERN
      value: "*-logs-*" # Matches both audit-logs-2023 and app-logs-2023
    ```
2.  LogSage uses this pattern in all search queries (`es.search(index=ES_INDEX_PATTERN, ...)`).

## 3. Production Deployment Optimizations
To handle high concurrent traffic to the Dashboard:

- **WSGI Server**: Use `gunicorn` instead of the development server.
    - Update `CMD` in Dockerfile: `CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "main:app"]`
    - Workers: `-w 4` allows parallel processing of requests.
- **Caching**: 
    - The `local_logs` fallback currently stores raw lists. For 5TB, do not rely on in-memory fallback for long-term storage; use it only as a buffer.
