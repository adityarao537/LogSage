# Kubernetes Deployment Troubleshooting Guide

This document captures common issues encountered when deploying LogSage to Kubernetes and their solutions. **This document is actively maintained** - all new issues and fixes are documented here.

## Table of Contents
1. [Elasticsearch Connection Issues](#elasticsearch-connection-issues)
2. [Python Dependency Conflicts](#python-dependency-conflicts)
3. [Elasticsearch Query Issues](#elasticsearch-query-issues)
4. [Application Runtime Errors](#application-runtime-errors)
5. [Dependency Validation](#dependency-validation)
6. [Diagnostic Tools](#diagnostic-tools)
7. [Common Deployment Workflow](#common-deployment-workflow)

---

## 📝 Maintaining This Document

**This guide is a living document.** When you encounter and fix a new issue:

1. **Add a new issue section** in the appropriate category (or create a new category)
2. **Include these details:**
   - **Symptoms**: Error messages, behavior observed
   - **Root Cause**: Why the issue occurred
   - **Diagnosis**: How to identify the issue
   - **Solution**: Step-by-step fix with code/config examples
3. **Update the Issues Summary table** at the bottom
4. **Update the Troubleshooting Checklist** if needed
5. **Update the Last Updated date** at the bottom

**Template for new issues:**
```markdown
### Issue X: [Brief Description]

**Symptoms:**
```
[Error messages or behavior]
```

**Root Cause:**
- [Explanation of why it happens]

**Solution:**
[Step-by-step fix with examples]
```

---

## Elasticsearch Connection Issues

### Issue 1: "Could not ping Elasticsearch" Warning

**Symptoms:**
```
Warning: Could not connect to Elasticsearch: Could not ping Elasticsearch. Using in-memory fallback.
```

**Root Cause:**
- Version mismatch between Elasticsearch Python client and Elasticsearch server
- The `ping()` method in newer Elasticsearch clients (8.x) doesn't work properly with ES 7.x servers
- Incorrect connection format (using deprecated dict format instead of URL)

**Diagnosis Steps:**

1. **Verify network connectivity** - Test if you can reach Elasticsearch from the pod:
   ```bash
   kubectl exec -n logsage <pod-name> -- telnet elasticsearch-master.logging.svc.cluster.local 9200
   ```

2. **Test HTTP connectivity** - Verify Elasticsearch responds to HTTP requests:
   ```bash
   kubectl exec -n logsage <pod-name> -- curl http://elasticsearch-master.logging.svc.cluster.local:9200
   ```
   
   Expected response:
   ```json
   {
     "name" : "elasticsearch-master-1",
     "cluster_name" : "rezprd",
     "cluster_uuid" : "...",
     "version" : {
       "number" : "7.8.0",
       ...
     }
   }
   ```

3. **Run diagnostic script** - Use the provided `test_es_connection.py` script:
   ```bash
   # Copy script to pod
   kubectl cp test_es_connection.py logsage/<pod-name>:/tmp/test_es_connection.py
   
   # Run diagnostic
   kubectl exec -n logsage <pod-name> -- python3 /tmp/test_es_connection.py
   ```

**Solution:**

1. **Pin Elasticsearch client version** to match your server version:
   ```
   # In requirements.txt
   elasticsearch==7.10.1  # For ES 7.x servers
   ```

2. **Use proper connection format** in `main.py`:
   ```python
   # ✓ CORRECT - URL format
   es_url = f"http://{ES_HOST}:{ES_PORT}"
   es = Elasticsearch([es_url], timeout=30, max_retries=3, retry_on_timeout=True)
   
   # ✗ WRONG - Deprecated dict format (doesn't work with newer clients)
   es = Elasticsearch([{'host': ES_HOST, 'port': ES_PORT, 'scheme': 'http'}])
   ```

3. **Use `es.info()` instead of `es.ping()`** for connection testing:
   ```python
   # ✓ CORRECT - More reliable
   info = es.info()
   print(f"Connected to cluster: {info.get('cluster_name')}")
   
   # ✗ UNRELIABLE - ping() returns False even when connection works
   if not es.ping():
       raise Exception("Could not ping")
   ```

---

## Python Dependency Conflicts

### Issue 2: NumPy 2.0 Incompatibility

**Symptoms:**
```
AttributeError: `np.float_` was removed in the NumPy 2.0 release. Use `np.float64` instead.
```

**Root Cause:**
- Elasticsearch 7.10.1 uses deprecated NumPy types (`np.float_`) that were removed in NumPy 2.0
- When no version is specified, pip installs the latest NumPy (2.x)

**Solution:**

Pin NumPy to a version before 2.0 in `requirements.txt`:
```
numpy<2.0
```

**Full Compatible Requirements:**
See [`backend/requirements.txt`](file:///c:/RateGain/github/LogSage/backend/requirements.txt) for the complete list with pinned versions and compatibility notes.

### Issue 3: Additional Dependency Conflicts

**Common conflicts and solutions:**

1. **Pandas + NumPy Version Mismatch**
   ```
   ImportError: numpy.core.multiarray failed to import
   ```
   - **Cause**: Pandas compiled against different NumPy version
   - **Fix**: Reinstall both together: `pip install --no-cache-dir 'numpy==1.24.3' 'pandas==2.0.3'`

2. **Scikit-learn + NumPy Incompatibility**
   ```
   ValueError: numpy.dtype size changed
   ```
   - **Cause**: Scikit-learn compiled against different NumPy
   - **Fix**: Reinstall scikit-learn: `pip uninstall scikit-learn && pip install --no-cache-dir 'scikit-learn==1.3.0'`

3. **OpenAI API Breaking Changes**
   ```
   AttributeError: 'OpenAI' object has no attribute 'ChatCompletion'
   ```
   - **Cause**: OpenAI 0.x → 1.x API changes
   - **Fix**: Code already uses 1.x API. Ensure `openai==1.12.0` is installed.

**For comprehensive dependency management**, see:
- [`DEPENDENCY_MANAGEMENT.md`](file:///c:/RateGain/github/LogSage/DEPENDENCY_MANAGEMENT.md) - Full version matrices, upgrade guides, and conflict resolution

---

## Dependency Validation

### Automated Validation Script

Use the validation script to check all dependencies before deployment:

```bash
# Run validation
python scripts/validate_dependencies.py
```

**What it checks:**
- ✅ Python version compatibility
- ✅ Package versions match requirements.txt
- ✅ Known incompatible combinations (e.g., ES 7.x + NumPy 2.0)
- ✅ All critical imports work
- ✅ Elasticsearch client version compatibility

**Example output:**
```
======================================================================
 LogSage Dependency Validation
======================================================================

======================================================================
Python Version Check
======================================================================
Current Python: 3.9.18
✅ PASS: Python version is compatible

======================================================================
Package Version Check
======================================================================
✅ flask                - 2.3.3      (matches)
✅ numpy                - 1.24.3     (matches)
✅ elasticsearch        - 7.10.1     (matches)
...

======================================================================
VALIDATION SUMMARY
======================================================================
✅ PASS - Python Version
✅ PASS - Package Versions
✅ PASS - Compatibility
✅ PASS - Imports
✅ PASS - Elasticsearch

Results: 5/5 checks passed

🎉 All validations passed! Dependencies are correctly configured.
```

---

## Elasticsearch Query Issues

### Issue 4: "No mapping found for [timestamp]" Error

**Symptoms:**
```
ES Fetch Failed (using fallback): RequestError(400, 'search_phase_execution_exception', 'No mapping found for [timestamp] in order to sort on')
```

**Root Cause:**
- The code is trying to sort by a `timestamp` field that doesn't exist in your Elasticsearch indices
- Different log sources use different timestamp field names:
  - **Filebeat/Logstash**: Use `@timestamp`
  - **Custom logs**: May use `timestamp`, `time`, or other field names
  - **LogSage native**: Uses `timestamp`

**Diagnosis:**

Check what timestamp field your indices actually use:

```bash
# Get index mapping
kubectl exec -n logsage <pod-name> -- curl http://elasticsearch-master.logging.svc.cluster.local:9200/rezgain-new-ui-*/_mapping?pretty

# Look for timestamp-related fields in the mapping
# Common field names: @timestamp, timestamp, time, eventTime, etc.
```

**Solution:**

Set the `ES_TIMESTAMP_FIELD` environment variable in your deployment:

```yaml
# deployment.yaml
env:
  - name: ES_TIMESTAMP_FIELD
    value: "@timestamp"  # Use the actual field name from your indices
```

**Common configurations:**

| Log Source | Timestamp Field | Configuration |
|------------|----------------|---------------|
| Filebeat | `@timestamp` | `ES_TIMESTAMP_FIELD=@timestamp` |
| Logstash | `@timestamp` | `ES_TIMESTAMP_FIELD=@timestamp` |
| Fluentd | `@timestamp` or `time` | Check your config |
| Custom apps | `timestamp` or `time` | Check your schema |
| LogSage native | `timestamp` | `ES_TIMESTAMP_FIELD=timestamp` |

**Graceful degradation:**
The code now handles missing timestamp fields gracefully - if sorting fails, it will fetch logs unsorted rather than failing completely.

---

## Application Runtime Errors

### Issue 5: Anomaly Detection Field Errors

**Symptoms:**
```
ERROR in /anomaly: 'service'
ERROR in /anomaly: 'component'
ERROR in /anomaly: 'level'
```

**Root Cause:**
- The anomaly detection feature expects logs to have specific fields: `service`, `component`, `level`, `message`
- Your existing Elasticsearch indices may use different field names or not have these fields at all
- The code was trying to access these fields without checking if they exist, causing KeyError

**Impact:**
- `/anomaly` endpoint fails
- Anomaly detection dashboard shows errors
- Application continues to work but without anomaly detection

**Solution:**

The code has been updated to handle missing fields gracefully:

```python
# Now handles missing fields with defaults
df['service'] = df.get('service', pd.Series(['unknown'] * len(df)))
df['component'] = df.get('component', pd.Series(['unknown'] * len(df)))
df['level'] = df.get('level', pd.Series(['INFO'] * len(df)))
```

**No configuration needed** - the fix is automatic. Logs without these fields will:
- Use `'unknown'` for missing `service` and `component`
- Use `'INFO'` for missing `level`
- Use empty string for missing `message`
- Still be analyzed for anomalies based on available data

**For better anomaly detection:**
If you want to map your existing fields to LogSage's expected fields, you can:
1. Add field mapping in Elasticsearch (alias fields)
2. Or modify the `detect_anomalies_batch()` function to use your field names

---

### Issue 6: OpenAI Client Compatibility Error

**Symptoms:**
```
TypeError: __init__() got an unexpected keyword argument 'proxies'
```

**Root Cause:**
- OpenAI client version 1.12.0 has breaking changes in httpx client initialization.
- **Critical**: httpx 0.28.x has breaking changes in the `proxies` argument that break OpenAI 1.3.0.

**Solution:**
Pin both `httpx` and `openai` in `requirements.txt`:
```txt
httpx<0.25
openai==1.3.0
```

---

### Issue 7: OpenAI API Connection Error / Timeout

**Symptoms:**
```
LLM Error in nl_to_es_query: Connection error.
LLM Error in nl_to_es_query: Request timed out.
```

**Root Cause:**
- Pod cannot reach `api.openai.com` due to network restrictions (Egress/NAT).
- Missing corporate proxy configuration.

**Solution:**
1. Verify egress access from the pod.
2. If a proxy is needed, update `ai_service.py` to use a proxied `httpx` client.

---

## Dependency Validation

### test_es_connection.py

A diagnostic script to test various Elasticsearch connection configurations:

**Location:** `test_es_connection.py` in project root

**Usage:**
```bash
# Copy to pod
kubectl cp test_es_connection.py logsage/<pod-name>:/tmp/test_es_connection.py

# Run inside pod
kubectl exec -n logsage <pod-name> -- python3 /tmp/test_es_connection.py
```

**What it tests:**
1. Basic HTTP/HTTPS connectivity using urllib
2. Elasticsearch Python client with different configurations:
   - HTTP without authentication
   - HTTPS without authentication
   - HTTP with basic auth
   - HTTPS with basic auth

**Output:**
- Shows which connection method works
- Displays cluster name and version if successful
- Helps identify if authentication or SSL is required

---

## Common Deployment Workflow

### After Making Code Changes:

1. **Rebuild Docker image:**
   ```bash
   docker build -t <ECR_URI>/logsage:latest .
   ```

2. **Push to ECR:**
   ```bash
   docker push <ECR_URI>/logsage:latest
   ```

3. **Restart deployment:**
   ```bash
   kubectl rollout restart deployment/logsage -n logsage
   ```

4. **Watch logs:**
   ```bash
   kubectl logs -f deployment/logsage -n logsage
   ```

5. **Get pod name if needed:**
   ```bash
   kubectl get pods -n logsage
   ```

### Expected Successful Startup Logs:

```
[2026-01-23 15:44:43 +0000] [1] [INFO] Starting gunicorn 23.0.0
[2026-01-23 15:44:43 +0000] [1] [INFO] Listening at: http://0.0.0.0:5000 (1)
[2026-01-23 15:44:43 +0000] [1] [INFO] Using worker: sync
[2026-01-23 15:44:43 +0000] [7] [INFO] Booting worker with pid: 7
Attempting to connect to Elasticsearch at: http://elasticsearch-master.logging.svc.cluster.local:9200
Elasticsearch client created, attempting to get cluster info...
✓ Connected to Elasticsearch cluster: rezprd, version: 7.8.0
✓ Elasticsearch connection successful!
```

---

## Environment Variables Reference

Required environment variables in `deployment.yaml`:

```yaml
env:
  - name: ELASTICSEARCH_HOST
    value: "elasticsearch-master.logging.svc.cluster.local"
  - name: ELASTICSEARCH_PORT
    value: "9200"
  - name: ES_INDEX_PATTERN
    value: "rezgain-new-ui-*"  # or "*" for all indexes
  - name: ES_TIMESTAMP_FIELD
    value: "@timestamp"  # Use "@timestamp" for Filebeat/Logstash, "timestamp" for custom
  - name: LLM_API_KEY
    value: "sk-proj-..."  # OpenAI API key
```

**Important Notes:**
- `ELASTICSEARCH_HOST` must be the full Kubernetes DNS name: `<service-name>.<namespace>.svc.cluster.local`
- Port should be `9200` for HTTP API (not 9300 which is for node-to-node communication)
- `ES_TIMESTAMP_FIELD` should match the actual timestamp field in your indices
- Ensure there are no extra quotes in YAML values

---

## Version Compatibility Matrix

| Component | Version | Notes |
|-----------|---------|-------|
| Elasticsearch Server | 7.8.0 | Production cluster version |
| elasticsearch (Python) | 7.10.1 | Must be 7.x to match server |
| NumPy | < 2.0 | ES 7.10.1 incompatible with NumPy 2.0 |
| Python | 3.9+ | As per Dockerfile |

---

## Quick Reference Commands

```bash
# Get pod name
kubectl get pods -n logsage

# View logs
kubectl logs -f <pod-name> -n logsage

# Execute command in pod
kubectl exec -n logsage <pod-name> -- <command>

# Copy file to pod
kubectl cp <local-file> logsage/<pod-name>:<remote-path>

# Describe pod (for troubleshooting)
kubectl describe pod <pod-name> -n logsage

# Get deployment status
kubectl get deployment logsage -n logsage

# Restart deployment
kubectl rollout restart deployment/logsage -n logsage
```

---

## Troubleshooting Checklist

### Pre-Deployment Checks
- [ ] Run dependency validation: `python scripts/validate_dependencies.py`
- [ ] All package versions match requirements.txt
- [ ] Docker image built successfully
- [ ] Image pushed to ECR

### Elasticsearch Connection Checks
- [ ] Can telnet to Elasticsearch from pod?
- [ ] Does curl to Elasticsearch return cluster info?
- [ ] Is Elasticsearch client version compatible with server? (7.x for ES 7.x)
- [ ] Is NumPy version < 2.0?
- [ ] Using `es.info()` instead of `es.ping()` for connection test?

### Configuration Checks
- [ ] Are environment variables set correctly in deployment.yaml?
- [ ] `ELASTICSEARCH_HOST` is full K8s DNS name
- [ ] `ES_INDEX_PATTERN` matches your indices
- [ ] `ES_TIMESTAMP_FIELD` matches your timestamp field name (`@timestamp` for Filebeat/Logstash)
- [ ] No syntax errors in deployment.yaml (extra quotes, etc.)?

### Deployment Checks
- [ ] Docker image rebuilt and pushed after code changes?
- [ ] Deployment restarted after image update?
- [ ] Pods are running (not CrashLoopBackOff)?
- [ ] Logs show successful ES connection?

### Runtime Checks
- [ ] `/logs` endpoint returns data?
- [ ] `/anomaly` endpoint works (no field errors)?
- [ ] `/query` endpoint works (no OpenAI errors)?
- [ ] No errors in pod logs?

---

## Issues Summary & Quick Reference

All issues documented in this guide with their current status:

| Issue # | Problem | Status | Quick Fix |
|---------|---------|--------|-----------|
| **1** | "Could not ping Elasticsearch" | ✅ RESOLVED | Use `elasticsearch==7.10.1`, `es.info()` instead of `ping()` |
| **2** | NumPy 2.0 incompatibility | ✅ RESOLVED | Pin `numpy==1.24.3` |
| **3** | Additional dependency conflicts | ✅ RESOLVED | See requirements.txt for all pinned versions |
| **4** | "No mapping found for [timestamp]" | ✅ RESOLVED | Set `ES_TIMESTAMP_FIELD=@timestamp` |
| **5** | Anomaly detection field errors | ✅ RESOLVED | Code now handles missing fields gracefully |
| **6** | OpenAI client 'proxies' error | ✅ RESOLVED | Pin `httpx<0.25` and `openai==1.3.0` |
| **7** | OpenAI connection/timeout | ⚠️ IN PROGRESS | Check Egress/Proxy settings |

### Quick Diagnosis Flow

```
Pod won't start?
├─ Check logs: kubectl logs <pod> -n logsage
├─ Import errors? → Check Issue #2, #3 (dependencies)
└─ Connection errors? → Check Issue #1 (ES connection)

Pod running but errors in logs?
├─ "No mapping found for [timestamp]"? → Issue #4
├─ "ERROR in /anomaly: 'service'"? → Issue #5
├─ "TypeError: proxies"? → Issue #6
└─ Other errors? → Check full logs and this guide

Application works but features broken?
├─ Anomaly detection fails? → Issue #5
├─ Natural language queries fail? → Issue #6
└─ Logs not showing? → Issue #4
```

---

## Getting Help

If you encounter a new issue not covered in this guide:

1. **Capture the error:**
   ```bash
   kubectl logs -f <pod-name> -n logsage > error.log
   ```

2. **Check the basics:**
   - Run validation script: `python scripts/validate_dependencies.py`
   - Verify environment variables in deployment.yaml
   - Check Elasticsearch connectivity

3. **Document the issue:**
   - Error message (full stack trace)
   - Steps to reproduce
   - Environment details (ES version, K8s version, etc.)

4. **Add to this guide:**
   - Document the issue in the appropriate section
   - Include symptoms, root cause, and solution
   - Update the Issues Summary table
   - Update the troubleshooting checklist if needed

---

## Related Documentation

- [`DEPENDENCY_MANAGEMENT.md`](file:///c:/RateGain/github/LogSage/DEPENDENCY_MANAGEMENT.md) - Comprehensive version management and upgrade guides
- [`DEPLOYMENT.md`](file:///c:/RateGain/github/LogSage/DEPLOYMENT.md) - Deployment instructions
- [`README.md`](file:///c:/RateGain/github/LogSage/README.md) - Project overview and features

---

*Last Updated: 2026-01-23*  
*This document is actively maintained. All deployment issues and their solutions are documented here.*
