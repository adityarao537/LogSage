

from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import LabelEncoder
import numpy as np
import datetime
import os
import sys
from elasticsearch import Elasticsearch, helpers

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

@app.route('/')
def home():
    return app.send_static_file('index.html')

# Elasticsearch Connection
# Elasticsearch Connection
ES_HOST = os.environ.get("ELASTICSEARCH_HOST", "localhost")
ES_PORT = int(os.environ.get("ELASTICSEARCH_PORT", 9200))
# Default to logsage-logs, but allow * for all indexes
INDEX_NAME = os.environ.get("ES_INDEX_PATTERN", "logsage-logs")
# Timestamp field name ("timestamp" for LogSage, "@timestamp" for Filebeat/Logstash)
TIMESTAMP_FIELD = os.environ.get("ES_TIMESTAMP_FIELD", "@timestamp") 

es = None
try:
    # Use proper URL format for Elasticsearch connection
    es_url = f"http://{ES_HOST}:{ES_PORT}"
    print(f"Attempting to connect to Elasticsearch at: {es_url}", file=sys.stderr)
    
    # Create ES client compatible with ES 7.x
    es = Elasticsearch(
        [es_url], 
        timeout=30, 
        max_retries=3, 
        retry_on_timeout=True
    )
    
    print(f"Elasticsearch client created, attempting to get cluster info...", file=sys.stderr)
    # Use info() instead of ping() - it's more reliable
    info = es.info()
    print(f"✓ Connected to Elasticsearch cluster: {info.get('cluster_name', 'unknown')}, version: {info.get('version', {}).get('number', 'unknown')}", file=sys.stderr)
    
    # Only create index if we are using the specific default one
    if INDEX_NAME == "logsage-logs" and not es.indices.exists(index=INDEX_NAME):
        es.indices.create(index=INDEX_NAME)
        print(f"Created index: {INDEX_NAME}", file=sys.stderr)
    
    print("✓ Elasticsearch connection successful!", file=sys.stderr)
except Exception as e:
    import traceback
    print(f"✗ Warning: Could not connect to Elasticsearch: {type(e).__name__}: {e}", file=sys.stderr)
    print(f"Full traceback: {traceback.format_exc()}", file=sys.stderr)
    print("Using in-memory fallback storage.", file=sys.stderr)
    es = None

# Encoders (kept for anomaly detection logic which might run on batch data)
le_service = LabelEncoder()
le_component = LabelEncoder()
le_level = LabelEncoder()
known_services = ["booking-api", "auth-service", "payment-gateway", "unknown"]
known_components = ["db", "cache", "queue", "unknown"]
known_levels = ["INFO", "WARN", "ERROR", "DEBUG", "FATAL"]
le_service.fit(known_services)
le_component.fit(known_components)
le_level.fit(known_levels)

def normalize_log(log):
    return {
        "timestamp": log.get("timestamp", datetime.datetime.utcnow().isoformat()),
        "service": log.get("service", "unknown"),
        "component": log.get("component", "unknown"),
        "level": log.get("level", "INFO"),
        "message": log.get("message", "")
    }

def detect_anomalies_batch(logs_data):
    if not logs_data:
        return []
    
    try:
        df = pd.DataFrame(logs_data)
        
        # Handle missing fields gracefully - use defaults if fields don't exist
        if 'message' not in df.columns:
            df['message'] = ''
        df['msg_len'] = df['message'].apply(lambda x: len(str(x)) if x else 0)
        
        # Extract fields with defaults for missing values
        df['service'] = df.get('service', pd.Series(['unknown'] * len(df)))
        df['component'] = df.get('component', pd.Series(['unknown'] * len(df)))
        df['level'] = df.get('level', pd.Series(['INFO'] * len(df)))
        
        # Fill NaN values with defaults
        df['service'] = df['service'].fillna('unknown')
        df['component'] = df['component'].fillna('unknown')
        df['level'] = df['level'].fillna('INFO')
        
        def safe_transform(le, col_data):
            new_labels = set(col_data) - set(le.classes_)
            if new_labels:
                le.classes_ = np.concatenate([le.classes_, list(new_labels)])
            return le.transform(col_data)

        df['service_enc'] = safe_transform(le_service, df['service'])
        df['component_enc'] = safe_transform(le_component, df['component'])
        df['level_enc'] = safe_transform(le_level, df['level'])
        
        features = ['msg_len', 'service_enc', 'component_enc', 'level_enc']
        X = df[features].values
        
        clf = IsolationForest(contamination=0.1, random_state=42)
        preds = clf.fit_predict(X)
        
        anomalies = []
        for idx, pred in enumerate(preds):
            if pred == -1:
                log_entry = logs_data[idx].copy()
                log_entry['anomaly_score'] = float(clf.decision_function([X[idx]])[0])
                anomalies.append(log_entry)
        return anomalies
    except Exception as e:
        print(f"Error in anomaly detection: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return []  # Return empty list on error instead of crashing

import sys

# In-memory fallback
local_logs = []

@app.route('/ingest', methods=['POST'])
def ingest_log():
    try:
        data = request.json
        logs_to_ingest = []
        if isinstance(data, list):
            for entry in data:
                logs_to_ingest.append(normalize_log(entry))
        else:
            logs_to_ingest.append(normalize_log(data))
        
        # Try ES first
        try:
            if es:
                actions = [{"_index": INDEX_NAME, "_source": log} for log in logs_to_ingest]
                helpers.bulk(es, actions)
                es_status = "Indexed to ES"
            else:
                 raise Exception("ES not initialized")
        except Exception as e:
            print(f"ES Ingest Failed (using fallback): {e}", file=sys.stderr)
            local_logs.extend(logs_to_ingest)
            es_status = "Saved to In-Memory"

        return jsonify({"status": "success", "message": f"Ingested {len(logs_to_ingest)} logs. ({es_status})"}), 201
    except Exception as e:
        print(f"ERROR in /ingest: {e}", file=sys.stderr)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/logs', methods=['GET'])
def get_logs():
    try:
        # Try ES
        if es:
            try:
                # Try with configured timestamp field, fallback to unsorted if field doesn't exist
                try:
                    res = es.search(index=INDEX_NAME, body={"query": {"match_all": {}}, "sort": [{TIMESTAMP_FIELD: "desc"}], "size": 100})
                except Exception as sort_error:
                    # If sorting fails, try without sort (field may not exist)
                    print(f"Sorting by {TIMESTAMP_FIELD} failed, fetching unsorted: {sort_error}", file=sys.stderr)
                    res = es.search(index=INDEX_NAME, body={"query": {"match_all": {}}, "size": 100})
                
                hits = [hit["_source"] for hit in res['hits']['hits']]
                return jsonify(hits)
            except Exception as e:
                print(f"ES Fetch Failed (using fallback): {e}", file=sys.stderr)
        
        # Fallback
        return jsonify(local_logs[-100:])
    except Exception as e:
        print(f"ERROR in /logs: {e}", file=sys.stderr)
        # Even if everything breaks, return empty list or local logs
        return jsonify(local_logs[-100:])

@app.route('/anomaly', methods=['GET'])
def detect_anomaly_endpoint():
    try:
        # Try ES
        logs_data = []
        if es:
            try:
                # Try with configured timestamp field, fallback to unsorted if field doesn't exist
                try:
                    res = es.search(index=INDEX_NAME, body={"query": {"match_all": {}}, "sort": [{TIMESTAMP_FIELD: "desc"}], "size": 500})
                except:
                    res = es.search(index=INDEX_NAME, body={"query": {"match_all": {}}, "size": 500})
                logs_data = [hit["_source"] for hit in res['hits']['hits']]
            except Exception:
                logs_data = local_logs[-500:]
        else:
            logs_data = local_logs[-500:]
        
        if not logs_data:
             return jsonify({
                "anomaly": False,
                "count": 0,
                "anomalies": []
            })

        anomalies = detect_anomalies_batch(logs_data)
        return jsonify({
            "anomaly": len(anomalies) > 0,
            "count": len(anomalies),
            "anomalies": anomalies
        })
    except Exception as e:
        print(f"ERROR in /anomaly: {e}", file=sys.stderr)
        return jsonify({"error": str(e)}), 500

import ai_service

# Natural Language Query Endpoint
@app.route('/query', methods=['POST'])
def nl_query():
    user_query = request.json.get("query", "").lower()
    
    # 1. Convert NL to ES DSL via AI Service
    es_query = ai_service.nl_to_es_query(user_query)
    
    # 2. Define Fallback Filter (Best effort match for fallback)
    fallback_filter = lambda l: True
    if "error" in user_query:
        fallback_filter = lambda l: l['level'] == 'ERROR'
    elif "warn" in user_query:
        fallback_filter = lambda l: l['level'] == 'WARN'
        
    try:
        if es:
            try:
                res = es.search(index=INDEX_NAME, body={"query": es_query, "size": 50})
                hits = [hit["_source"] for hit in res['hits']['hits']]
                return jsonify({
                    "query": user_query,
                    "es_query": es_query,
                    "results": hits
                })
            except Exception as e:
                print(f"ES Chat Query Failed (using fallback): {e}", file=sys.stderr)
        
        # Fallback: Filter local_logs
        hits = [log for log in local_logs if fallback_filter(log)]
        hits.sort(key=lambda x: x['timestamp'], reverse=True)
        return jsonify({
            "query": user_query,
            "es_query": "FALLBACK_IN_MEMORY",
            "results": hits[:50]
        })

    except Exception as e:
        print(f"ERROR in /query: {e}", file=sys.stderr)
        return jsonify({"error": str(e)}), 500

@app.route('/diagnose', methods=['POST'])
def diagnose_log():
    log_entry = request.json.get("log")
    if not log_entry:
        return jsonify({"error": "No log provided"}), 400
    
    diagnosis = ai_service.analyze_anomaly(log_entry)
    return jsonify({"diagnosis": diagnosis})




if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
