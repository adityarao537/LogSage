import os
import json
import sys

# Optional: Import OpenAI if available, else Mock
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

LLM_API_KEY = os.environ.get("LLM_API_KEY")

def get_llm_client():
    if LLM_API_KEY and OpenAI:
        return OpenAI(api_key=LLM_API_KEY)
    return None

def mock_nl_to_es_query(user_query):
    """
    Mock logic to convert NL to ES DSL if no LLM is available.
    """
    user_query = user_query.lower()
    if "error" in user_query:
        return {"match": {"level": "ERROR"}}
    elif "warn" in user_query:
        return {"match": {"level": "WARN"}}
    elif "payment" in user_query:
        return {"match": {"service": "payment-gateway"}}
    elif "db" in user_query or "database" in user_query:
        return {"match": {"component": "db"}}
    return {"match_all": {}}

def nl_to_es_query(user_query):
    """
    Uses LLM to convert Natural Language to Elasticsearch DSL.
    """
    client = get_llm_client()
    if not client:
        print("Using Mock AI for Query", file=sys.stderr)
        return mock_nl_to_es_query(user_query)
    
    prompt = f"""
    You are an expert in Elasticsearch. Convert the following natural language query into a raw Elasticsearch Query DSL JSON object (content of the 'query' field only).
    Do not wrap in markdown or code blocks. Return ONLY valid JSON.
    
    Fields available: timestamp (date), level (keyword), service (keyword), component (keyword), message (text).
    
    Query: "{user_query}"
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        content = response.choices[0].message.content.strip()
        # Clean potential markdown
        if content.startswith("```json"):
            content = content[7:-3]
        elif content.startswith("```"):
            content = content[3:-3]
            
        return json.loads(content)
    except Exception as e:
        print(f"LLM Error in nl_to_es_query: {e}", file=sys.stderr)
        return mock_nl_to_es_query(user_query)

def analyze_anomaly(log_entry):
    """
    Uses LLM to diagnose a specific log entry.
    """
    client = get_llm_client()
    if not client:
        return "AI Diagnosis (Mock): Check downstream dependencies and latency."
    
    prompt = f"""
    Analyze this log entry which was flagged as an anomaly. Provide a brief 1-sentence diagnosis and a recommendation.
    
    Log: {json.dumps(log_entry)}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"LLM Error in analyze_anomaly: {e}", file=sys.stderr)
        return "AI Diagnosis: Could not analyze due to API error."
