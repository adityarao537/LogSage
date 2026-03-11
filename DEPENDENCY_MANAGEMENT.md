# Dependency Management Guide

This guide provides comprehensive information for managing Python dependencies in LogSage across different Elasticsearch versions and deployment scenarios.

## Quick Start

**Current Configuration (Production):**
- **Elasticsearch Server:** 7.8.0
- **Python:** 3.9+
- **Key Constraint:** `numpy<2.0` (ES 7.10.1 incompatible with NumPy 2.0)

All dependencies are pinned in [`requirements.txt`](file:///c:/RateGain/github/LogSage/backend/requirements.txt) for reproducible builds.

---

## Version Compatibility Matrix

### Elasticsearch Client vs Server Versions

| ES Server Version | Python Client | NumPy Constraint | Pandas | Scikit-learn | Notes |
|-------------------|---------------|------------------|--------|--------------|-------|
| **6.8.x** | `elasticsearch==6.8.2` | `<1.24` | `1.5.3` | `1.2.2` | Legacy, use only if required |
| **7.x (7.8.0)** ✅ | `elasticsearch==7.10.1` | `<2.0` | `2.0.3` | `1.3.0` | **CURRENT - Production** |
| **8.x (8.0+)** | `elasticsearch==8.12.0` | `>=1.23` | `2.2.0` | `1.4.0` | Future upgrade path |

✅ = Currently deployed configuration

### Python Version Support

| Python Version | ES 6.8.2 | ES 7.10.1 | ES 8.12.0 | Recommended |
|----------------|----------|-----------|-----------|-------------|
| 3.8 | ✅ | ✅ | ❌ | No (EOL) |
| 3.9 | ✅ | ✅ | ✅ | **Yes** ✅ |
| 3.10 | ⚠️ | ✅ | ✅ | Yes |
| 3.11 | ❌ | ✅ | ✅ | Yes |
| 3.12 | ❌ | ⚠️ | ✅ | Future |

- ✅ Fully supported and tested
- ⚠️ Works but not officially tested
- ❌ Not compatible

---

## Dependency Details

### Critical Dependencies

#### 1. **elasticsearch**

The Elasticsearch Python client **must match the server's major version** for API compatibility.

**Version Selection:**
```python
# For ES 7.8.0 server ← CURRENT
elasticsearch==7.10.1

# For ES 6.8.x server
elasticsearch==6.8.2

# For ES 8.x server
elasticsearch==8.12.0
```

**Breaking Changes:**
- **6.x → 7.x**: Deprecated API endpoints removed
- **7.x → 8.x**: Connection format changed, authentication required by default

#### 2. **numpy**

NumPy 2.0 introduced breaking changes that affect Elasticsearch 7.x client.

**The Issue:**
```python
# Elasticsearch 7.10.1 internal code uses:
np.float_  # ← Removed in NumPy 2.0

# This causes:
AttributeError: `np.float_` was removed in the NumPy 2.0 release
```

**Solution:**
```
# For ES 7.x
numpy==1.24.3  # Last stable 1.x version

# For ES 8.x (NumPy 2.0 compatible)
numpy>=1.23,<2.1
```

#### 3. **pandas**

Pandas has tight coupling with NumPy versions.

**Compatibility:**
- `pandas==2.0.3` works with `numpy==1.24.3` ✅
- `pandas<1.5` required for `numpy<1.20`
- `pandas>=2.2` requires `numpy>=1.23`

#### 4. **scikit-learn**

Used for anomaly detection (`IsolationForest`).

**Compatibility:**
- `scikit-learn==1.3.0` works with `numpy==1.24.3` ✅
- Requires NumPy for matrix operations
- Version 1.4+ requires NumPy 1.23+

#### 5. **openai**

OpenAI client for AI features (NLQ, anomaly diagnosis).

**Version Notes:**
- `openai==1.12.0` - Stable 1.x API ✅
- `openai>=1.0.0` - New unified API (different from 0.x)
- Pin to avoid breaking changes in minor updates

---

## Elasticsearch Version Adaptation Guide

### Upgrading from ES 7.x to 8.x

#### Step 1: Update requirements.txt

```diff
# requirements.txt changes
-elasticsearch==7.10.1
+elasticsearch==8.12.0

-numpy==1.24.3
+numpy==1.26.4

-pandas==2.0.3
+pandas==2.2.0

-scikit-learn==1.3.0
+scikit-learn==1.4.0
```

#### Step 2: Update Connection Code

**ES 7.x code (current):**
```python
es = Elasticsearch(
    ["http://host:9200"],
    timeout=30,
    max_retries=3,
    retry_on_timeout=True
)
```

**ES 8.x code (required changes):**
```python
from elasticsearch import Elasticsearch

es = Elasticsearch(
    "http://host:9200",  # ← Single string, not list
    request_timeout=30,   # ← renamed from timeout
    max_retries=3,
    retry_on_timeout=True,
    # If ES 8.x has security enabled (default):
    basic_auth=("elastic", "password"),
    verify_certs=False  # For self-signed certs
)
```

#### Step 3: Update API Calls

ES 8.x uses the new object-based API:

```python
# ES 7.x (current)
es.indices.create(index="my-index")
result = es.search(index="my-index", body={"query": {...}})

# ES 8.x (new)
es.indices.create(index="my-index")
result = es.search(index="my-index", query={...})  # ← No 'body' param
```

#### Step 4: Test & Validate

```bash
# Rebuild with new dependencies
docker build -t logsage:test .

# Test locally first
docker run -e ELASTICSEARCH_HOST=test-es-host logsage:test

# Validate all endpoints work
python scripts/validate_dependencies.py
```

### Downgrading from ES 7.x to 6.x

#### Requirements Changes:

```diff
-elasticsearch==7.10.1
+elasticsearch==6.8.2

-numpy==1.24.3
+numpy==1.19.5

-pandas==2.0.3
+pandas==1.5.3

-scikit-learn==1.3.0
+scikit-learn==1.2.2
```

#### Code Changes:

ES 6.x uses similar API to ES 7.x, minimal changes needed:

```python
# Connection (same for 6.x and 7.x)
es = Elasticsearch(
    ["http://host:9200"],
    timeout=30
)
```

**Note:** Some newer query DSL features in ES 7.x may not work in 6.x.

---

## Dependency Upgrade Procedures

### Safe Upgrade Process

1. **Create a feature branch**
   ```bash
   git checkout -b upgrade/elasticsearch-8
   ```

2. **Update requirements.txt** with new versions

3. **Test locally** with docker-compose
   ```bash
   docker-compose down
   docker-compose build
   docker-compose up
   ```

4. **Run validation**
   ```bash
   python scripts/validate_dependencies.py
   ```

5. **Manual testing checklist:**
   - [ ] `/ingest` endpoint works
   - [ ] `/logs` retrieval works
   - [ ] `/anomaly` detection works
   - [ ] `/query` NLQ works
   - [ ] `/diagnose` AI analysis works

6. **Deploy to staging** (if available)
   ```bash
   # Build and push
   docker build -t <ecr-uri>/logsage:staging .
   docker push <ecr-uri>/logsage:staging
   
   # Deploy to staging namespace
   kubectl apply -f infra/k8s/ -n logsage-staging
   ```

7. **Monitor staging logs** for errors
   ```bash
   kubectl logs -f deployment/logsage -n logsage-staging
   ```

8. **Production deployment** only after staging validation
   ```bash
   docker tag <ecr-uri>/logsage:staging <ecr-uri>/logsage:latest
   docker push <ecr-uri>/logsage:latest
   kubectl rollout restart deployment/logsage -n logsage
   ```

### Rollback Procedure

If issues occur after upgrade:

```bash
# Revert requirements.txt
git checkout main -- backend/requirements.txt

# Rebuild with old versions
docker build -t <ecr-uri>/logsage:rollback .
docker push <ecr-uri>/logsage:rollback

# Update deployment to use rollback image
kubectl set image deployment/logsage logsage=<ecr-uri>/logsage:rollback -n logsage

# Watch rollback progress
kubectl rollout status deployment/logsage -n logsage
```

---

## Common Dependency Conflicts

### Issue 1: NumPy Version Conflicts

**Symptoms:**
```
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed.
This behavior is the source of the following dependency conflicts.
elasticsearch 7.10.1 requires numpy<2.0, but you have numpy 2.1.0
```

**Cause:** Conflicting NumPy requirements from multiple packages

**Solution:**
```bash
# Force specific NumPy version
pip install 'numpy==1.24.3' --force-reinstall

# Or update requirements.txt with explicit constraint
numpy==1.24.3  # Not just numpy<2.0
```

### Issue 2: Pandas and NumPy Mismatch

**Symptoms:**
```
ImportError: numpy.core.multiarray failed to import
```

**Cause:** Pandas compiled against different NumPy version

**Solution:**
```bash
# Reinstall both together
pip install --no-cache-dir 'numpy==1.24.3' 'pandas==2.0.3'
```

### Issue 3: Scikit-learn Compatibility

**Symptoms:**
```
ValueError: numpy.dtype size changed
```

**Cause:** Scikit-learn compiled against different NumPy

**Solution:**
```bash
# Reinstall scikit-learn with current NumPy
pip uninstall scikit-learn
pip install --no-cache-dir 'scikit-learn==1.3.0'
```

### Issue 4: OpenAI Breaking Changes

**Symptoms:**
```
AttributeError: 'OpenAI' object has no attribute 'ChatCompletion'
```

**Cause:** OpenAI 0.x → 1.x API changes

**Solution:**
Update code to use new API:
```python
# Old (0.x)
openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[...])

# New (1.x) ✅
client = OpenAI(api_key=key)
client.chat.completions.create(model="gpt-3.5-turbo", messages=[...])
```

---

## Diagnostic Tools

### 1. Validate Dependencies

```bash
# Check installed versions
pip list | grep -E "elasticsearch|numpy|pandas|scikit-learn|openai"

# Compare with requirements
pip check

# Run validation script
python scripts/validate_dependencies.py
```

### 2. Test Imports

```bash
# Quick import test
python -c "from elasticsearch import Elasticsearch; import numpy as np; import pandas as pd; from sklearn.ensemble import IsolationForest; from openai import OpenAI; print('✓ All imports successful')"
```

### 3. Check Compatibility

```python
# Get version info
import sys, numpy, pandas, sklearn, elasticsearch, openai

print(f"Python: {sys.version}")
print(f"NumPy: {numpy.__version__}")
print(f"Pandas: {pandas.__version__}")
print(f"Scikit-learn: {sklearn.__version__}")
print(f"Elasticsearch: {elasticsearch.__version__}")
print(f"OpenAI: {openai.__version__}")
```

---

## Requirements File Templates

### Production (ES 7.x - Current)

See [`backend/requirements.txt`](file:///c:/RateGain/github/LogSage/backend/requirements.txt)

### Development Requirements

For local development with additional tools:

```txt
# Production dependencies
-r requirements.txt

# Development only
pytest==7.4.0
pytest-cov==4.1.0
black==23.7.0
flake8==6.0.0
ipython==8.14.0
```

Save as `requirements-dev.txt`, install with:
```bash
pip install -r backend/requirements-dev.txt
```

---

## Best Practices

### ✅ DO:
- **Pin all versions** in production `requirements.txt`
- **Test upgrades** in staging before production
- **Document** why specific versions are required
- **Use version ranges** only for development
- **Keep NumPy compatible** with Elasticsearch client
- **Validate** after any dependency changes

### ❌ DON'T:
- **Mix major versions** (e.g., ES 8.x client with ES 7.x server)
- **Use `latest`** tags in production
- **Upgrade all at once** - do incremental updates
- **Skip testing** after dependency changes
- **Ignore deprecation warnings**
- **Use development dependencies** in production images

---

## CI/CD Integration

### Dockerfile Best Practices

**Current Dockerfile (good):**
```dockerfile
FROM python:3.9-slim
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```

**Production hardening:**
```dockerfile
FROM python:3.9-slim

# Use specific pip version for reproducibility
RUN pip install --upgrade pip==23.2.1

# Install dependencies with hash checking (optional)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

# Or use pip-compile for lock files
COPY backend/requirements.in .
RUN pip-compile requirements.in
RUN pip install -r requirements.txt
```

### Dependency Caching

Speed up builds with layer caching:
```dockerfile
# Copy requirements first (changes less frequently)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code second (changes more frequently)
COPY backend/ .
```

---

## Emergency Hotfix Guide

If production breaks due to dependency issues:

### Immediate Actions:

1. **Rollback to last known good image**
   ```bash
   kubectl rollout undo deployment/logsage -n logsage
   ```

2. **Check pod logs** for exact error
   ```bash
   kubectl logs -f deployment/logsage -n logsage | grep -i "error\|failed"
   ```

3. **Identify problematic dependency**
   - NumPy version mismatch → Check NumPy constraint
   - Import errors → Check package compatibility
   - ES connection failure → Check ES client version

4. **Quick fix in emergency:**
   ```bash
   # Create hotfix branch
   git checkout -b hotfix/dependency-fix
   
   # Fix requirements.txt
   # Rebuild and deploy (skip staging in emergency)
   docker build -t <ecr>/logsage:hotfix .
   docker push <ecr>/logsage:hotfix
   
   # Deploy immediately
   kubectl set image deployment/logsage logsage=<ecr>/logsage:hotfix -n logsage
   ```

5. **Post-incident:**
   - Document what happened
   - Add to TROUBLESHOOTING.md
   - Update validation scripts to catch this issue
   - Plan proper fix for next release

---

## Additional Resources

- [Elasticsearch Python Client Docs](https://elasticsearch-py.readthedocs.io/)
- [NumPy 2.0 Migration Guide](https://numpy.org/devdocs/numpy_2_0_migration_guide.html)
- [Pandas Compatibility](https://pandas.pydata.org/docs/whatsnew/index.html)
- [OpenAI Python SDK Changelog](https://github.com/openai/openai-python/releases)

---

## FAQ

**Q: Why pin exact versions instead of using `>=`?**  
A: Exact versions ensure reproducible builds. Unpinned versions can break production unexpectedly.

**Q: How often should we update dependencies?**  
A: Review quarterly for security updates. Major version upgrades should be planned projects.

**Q: Can I use NumPy 2.0 with ES 7.x?**  
A: No. ES 7.x client uses `np.float_` which was removed in NumPy 2.0. You must use `numpy<2.0`.

**Q: What if I need to use a different Python version?**  
A: Update the Dockerfile base image and test all dependencies. Python 3.10+ is recommended for new deployments.

**Q: How do I add a new Python package?**  
A: Add to requirements.txt with pinned version, test locally, validate no conflicts, deploy to staging, then production.

---

*Last Updated: 2026-01-23*  
*For deployment issues, see [TROUBLESHOOTING.md](file:///c:/RateGain/github/LogSage/TROUBLESHOOTING.md)*
