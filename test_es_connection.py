#!/usr/bin/env python3
"""
Quick script to test Elasticsearch connectivity with different configurations.
Run this inside your pod to diagnose the connection issue.
"""
import sys
import os

# Test 1: Basic HTTP request
print("=" * 60)
print("Test 1: Testing basic HTTP connectivity")
print("=" * 60)
try:
    import urllib.request
    es_host = os.environ.get("ELASTICSEARCH_HOST", "elasticsearch-master.logging.svc.cluster.local")
    es_port = os.environ.get("ELASTICSEARCH_PORT", "9200")
    
    for scheme in ['http', 'https']:
        url = f"{scheme}://{es_host}:{es_port}"
        print(f"\nTrying {url}...")
        try:
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=5) as response:
                data = response.read().decode('utf-8')
                print(f"✓ SUCCESS! Response: {data[:200]}")
                break
        except Exception as e:
            print(f"✗ Failed: {type(e).__name__}: {e}")
except Exception as e:
    print(f"HTTP test failed: {e}")

# Test 2: Elasticsearch Python client with different configs
print("\n" + "=" * 60)
print("Test 2: Testing Elasticsearch Python client")
print("=" * 60)

try:
    from elasticsearch import Elasticsearch
    
    es_host = os.environ.get("ELASTICSEARCH_HOST", "elasticsearch-master.logging.svc.cluster.local")
    es_port = os.environ.get("ELASTICSEARCH_PORT", "9200")
    
    configs = [
        {
            "name": "HTTP without auth",
            "url": f"http://{es_host}:{es_port}",
            "params": {"verify_certs": False}
        },
        {
            "name": "HTTPS without auth",
            "url": f"https://{es_host}:{es_port}",
            "params": {"verify_certs": False, "ssl_show_warn": False}
        },
        {
            "name": "HTTP with basic auth (elastic/changeme)",
            "url": f"http://{es_host}:{es_port}",
            "params": {"basic_auth": ("elastic", "changeme"), "verify_certs": False}
        },
        {
            "name": "HTTPS with basic auth (elastic/changeme)",
            "url": f"https://{es_host}:{es_port}",
            "params": {"basic_auth": ("elastic", "changeme"), "verify_certs": False, "ssl_show_warn": False}
        }
    ]
    
    for config in configs:
        print(f"\nTrying: {config['name']}")
        print(f"URL: {config['url']}")
        try:
            es = Elasticsearch([config['url']], **config['params'], request_timeout=10)
            result = es.ping()
            if result:
                print(f"✓ SUCCESS! Ping returned: {result}")
                # Try to get cluster info
                info = es.info()
                print(f"✓ Cluster info: {info.get('cluster_name', 'N/A')}, version: {info.get('version', {}).get('number', 'N/A')}")
                print("\n" + "=" * 60)
                print("SOLUTION FOUND! Use this configuration:")
                print("=" * 60)
                print(f"URL: {config['url']}")
                print(f"Params: {config['params']}")
                break
            else:
                print(f"✗ Ping returned False")
        except Exception as e:
            print(f"✗ Failed: {type(e).__name__}: {e}")
            
except Exception as e:
    print(f"Elasticsearch client test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Diagnostic complete!")
print("=" * 60)
