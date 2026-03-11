# Deploying LogSage to Amazon EKS

This guide will help you deploy LogSage alongside an existing ELK cluster on Amazon EKS.

## Prerequisites
- **AWS CLI** configured with access to your EKS cluster.
- **kubectl** installed and authenticated to your cluster.
- **Docker** installed.
- An **Amazon ECR** repository (or other container registry) to host the image.

## Step 1: Build and Push Docker Image

1.  **Authenticate Docker to ECR**:
    ```bash
    aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <aws_account_id>.dkr.ecr.<region>.amazonaws.com
    ```

2.  **Build the Image**:
    Navigate to the project root (`LogSage/`) and build:
    ```bash
    docker build -t logsage-app -f infra/Dockerfile .
    ```

3.  **Tag and Push**:
    ```bash
    docker tag logsage-app:latest <aws_account_id>.dkr.ecr.<region>.amazonaws.com/logsage-app:latest
    docker push <aws_account_id>.dkr.ecr.<region>.amazonaws.com/logsage-app:latest
    ```

## Step 2: Kubernetes Deployment Manifests

Create a file named `k8s-logsage.yaml` with the following content.

**Note**: You must replace `<ELASTICSEARCH_HOST>` with the internal DNS name of your existing Elasticsearch service in EKS (e.g., `elasticsearch-master.default.svc.cluster.local`) and `<IMAGE_URI>` with your ECR image URI.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: logsage
spec:
  replicas: 1
  selector:
    matchLabels:
      app: logsage
  template:
    metadata:
      labels:
        app: logsage
    spec:
      containers:
      - name: logsage
        image: <IMAGE_URI> # e.g., 123456789012.dkr.ecr.us-east-1.amazonaws.com/logsage-app:latest
        ports:
        - containerPort: 5000
        env:
        - name: ELASTICSEARCH_HOST
          value: "<ELASTICSEARCH_HOST>" # Point to your ELK Service
        - name: ELASTICSEARCH_PORT
          value: "9200"
        - name: ES_INDEX_PATTERN
          value: "*" # Set to "*" to scan all indexes, or "filebeat-*" etc.
        - name: LLM_API_KEY
          value: "<YOUR_LLM_API_KEY>" # Required for Agentic AI (OpenAI/DeepSeek)
---
apiVersion: v1
kind: Service
metadata:
  name: logsage-service
spec:
  type: LoadBalancer # Or ClusterIP if using an Ingress
  selector:
    app: logsage
  ports:
    - protocol: TCP
      port: 80
      targetPort: 5000
```

## Step 3: Deploy to EKS

1.  **Apply the Manifest**:
    ```bash
    kubectl apply -f k8s-logsage.yaml
    ```

2.  **Verify Deployment**:
    ```bash
    kubectl get pods
    kubectl get svc logsage-service
    ```
    Wait for the `EXTERNAL-IP` of the LoadBalancer Service to appear.

3.  **Access LogSage**:
    Open the External IP in your browser. The dashboard should load and connect to your internal ELK cluster.

## Configuration Notes
- **Agentic AI**:
    - Set `LLM_API_KEY` to enable the AI Chat and Diagnosis features.
    - If omitted, the system falls back to a "Mock Agent".
- **Production Ready**:
    - The Docker image uses **Gunicorn** (4 workers) by default for high concurrency.
    - **Frontend**: Served directly by the backend container (no separate Nginx needed).
- **Elasticsearch Access**: 
    - Ensure the LogSage pods have network access to your ELK cluster.
    - Use the **Service name** that handles client requests (e.g., `elasticsearch-master` or `elasticsearch-coordinating`).
- **High Scale**:
    - See `HIGH_SCALE.md` for architecture details on handling 5TB+ loads.
- **Environment Variables**:
    - `ELASTICSEARCH_HOST`: The internal K8s DNS name. **Format must be**: `<service-name>.<namespace>.svc.cluster.local`. (It does NOT accept `namespace/service_name`).
    - `ELASTICSEARCH_PORT`: Default 9200.
    - `ES_INDEX_PATTERN`: Default `logsage-logs`. Set to `*` to scan everything.

---

## Local Deployment (Docker Compose)

To run LogSage locally with your existing ELK stack:

1.  **Configure Environment**:
    Open `docker-compose.yml` and ensure `ELASTICSEARCH_HOST` points to your local ES (usually `host.docker.internal`).

2.  **Add Secrets (Optional)**:
    Create a `.env` file in the root directory:
    ```bash
    LLM_API_KEY=sk-your-key-here
    ES_INDEX_PATTERN=*
    ```

3.  **Run**:
    ```bash
    docker-compose up --build
    ```

4.  **Access**:
    Open [http://localhost:5000](http://localhost:5000).
    - Code changes in `backend/` or `frontend/` will hot-reload (volume mounted).
