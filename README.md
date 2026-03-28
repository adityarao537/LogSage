<p align="center">
  <img src="frontend/assets/logo/logo.png" width="250" alt="LogSage Logo">
</p>

# LogSage

An AI-Based Log Observability Platform.

## 🚀 Impact

LogSage revolutionizes how development and operations teams interact with their log data.
- **Natural Language Querying (NLQ)**: Say goodbye to writing complex Lucene or KQL queries. Ask questions in plain English (e.g., "Show me all 500 errors from the payment service") and get immediate results.
- **Agentic AI Diagnostics**: Automatically identify root causes of anomalies and errors using integrated LLMs (such as OpenAI or DeepSeek).
- **High-Scale Ready**: Designed to seamlessly integrate with your existing ELK stack, scaling effortlessly to handle 5TB+ of log data on Kubernetes environments.
- **Reduced Mean Time To Resolution (MTTR)**: Fast-track troubleshooting by surfacing critical insights from an ocean of logs directly to a centralized web dashboard.

## 🏗️ Architecture

```mermaid
graph TD
    subgraph Log Sources
        Apps[Microservices / Applications]
    end

    subgraph Ingestion
        Logstash[Logstash / Filebeat]
    end

    subgraph Storage Stack
        ES[(Elasticsearch Cluster)]
    end

    subgraph LogSage Platform
        Backend[LogSage Backend\n(Python/Flask/Gunicorn)]
        Frontend[Web Dashboard\n(HTML/JS)]
    end

    subgraph External
        LLM[LLM Provider API\n(OpenAI/DeepSeek)]
    end

    Apps -->|Logs| Logstash
    Logstash -->|Index| ES
    Backend <-->|Query| ES
    Backend <-->|NLQ & Insights| LLM
    Frontend <-->|REST API| Backend
```

## 🛠️ Installation & Setup

LogSage is designed to run alongside your existing Elasticsearch or ELK stack.

### 1. Local Deployment (Docker Compose)

The easiest way to run LogSage locally for testing or development.

1. Clone the repository and navigate to the project root:
   ```bash
   cd LogSage
   ```
2. Create a `.env` file in the root directory to provide your LLM API Key and Elasticsearch details:
   ```bash
   LLM_API_KEY=your-api-key-here
   ELASTICSEARCH_HOST=host.docker.internal # Or point to your local ES host
   ES_INDEX_PATTERN=*
   ```
3. Run with Docker Compose:
   ```bash
   docker-compose up --build
   ```
4. Open your browser and navigate to `http://localhost:5000`.

### 2. Kubernetes Deployment (Production)

To deploy LogSage in a production Kubernetes (e.g., Amazon EKS) environment alongside your ELK cluster:

1. **Build and push the Docker image** to your container registry (e.g., Amazon ECR).
   ```bash
   docker build -t logsage-app -f Dockerfile .
   docker tag logsage-app:latest <your-registry>/logsage-app:latest
   docker push <your-registry>/logsage-app:latest
   ```

2. **Configure your Kubernetes manifests**. Define the `ELASTICSEARCH_HOST` environment variable to point to your internal Elasticsearch service DNS (e.g., `elasticsearch-master.default.svc.cluster.local`). Detailed examples are in `DEPLOYMENT.md`.

3. **Deploy using kubectl**:
   ```bash
   kubectl apply -f k8s-logsage.yaml
   ```

4. **Verify and Access**: Wait for the LoadBalancer or Ingress to assign an external IP, then access the dashboard through your browser.

For more detailed deployment configurations, including high availability details, refer to [DEPLOYMENT.md](DEPLOYMENT.md) and [HIGH_SCALE.md](HIGH_SCALE.md).
