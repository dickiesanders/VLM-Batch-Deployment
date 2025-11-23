# DeepSeek OCR API

Complete documentation for the DeepSeek OCR API - a real-time document OCR and structured extraction service powered by DeepSeek-VL2 and vLLM.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Authentication](#authentication)
- [API Reference](#api-reference)
- [SDKs](#sdks)
- [Webhooks](#webhooks)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Administration](#administration)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)

---

## Overview

### Features

- **Real-time extraction**: Synchronous API for immediate results
- **Async processing**: Background jobs with webhook notifications
- **Batch processing**: Process entire S3/GCS buckets
- **Structured output**: Custom JSON schemas for data extraction
- **Multi-tenant**: Schema management with API key authentication
- **Rate limiting**: Per-tenant RPM/RPD quotas
- **A/B testing**: Compare model variants with metrics
- **BYOM**: Bring Your Own Model support
- **Team management**: Organizations with role-based access
- **Billing**: Stripe integration with usage-based pricing
- **Audit logging**: Compliance-ready action tracking

### Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│  FastAPI    │────▶│   vLLM      │
│             │     │   Server    │     │  DeepSeek   │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
       ┌──────────┐ ┌──────────┐ ┌──────────┐
       │  Redis   │ │ Postgres │ │ Storage  │
       │  (Jobs)  │ │(Schemas) │ │ (S3/GCS) │
       └──────────┘ └──────────┘ └──────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.12+
- NVIDIA GPU with CUDA support
- uv package manager

### Installation

```bash
# Clone repository
git clone https://github.com/dickiesanders/VLM-Batch-Deployment.git
cd VLM-Batch-Deployment

# Install dependencies
uv sync
```

### Download Models (Required)

**Important**: Models must be downloaded before starting the API for fast startup. The API will be slow on first run if models aren't pre-cached.

```bash
# Download your chosen model (do this once)
huggingface-cli download deepseek-ai/deepseek-vl2-tiny

# Or for better quality (requires more VRAM)
huggingface-cli download deepseek-ai/deepseek-vl2-small
```

Models are cached to `~/.cache/huggingface/`. Download sizes:
- `deepseek-vl2-tiny` - ~3GB
- `deepseek-vl2-small` - ~8GB
- `deepseek-vl2` - ~20GB+

For production deployments, include the model in your Docker image or mount a volume with pre-downloaded weights.

### Run Locally

```bash
# Start the API server
MODEL_NAME=deepseek-ai/deepseek-vl2-tiny uv run python -m api.main

# Server runs at http://localhost:8080
```

### First API Call

```bash
# Health check
curl http://localhost:8080/health

# Extract text from image
curl -X POST http://localhost:8080/ocr/extract \
  -H "Content-Type: application/json" \
  -H "X-API-Key: demo:secret" \
  -d '{
    "image_url": "https://example.com/document.png",
    "prompt": "Extract all text from this document"
  }'
```

---

## Authentication

### API Key Format

All API requests require authentication via the `X-API-Key` header:

```
X-API-Key: <tenant_id>:<secret>
```

Example: `X-API-Key: acme-corp:sk_live_abc123xyz`

### Creating API Keys

```bash
curl -X POST http://localhost:8080/api-keys \
  -H "Content-Type: application/json" \
  -H "X-API-Key: admin-tenant:admin-secret" \
  -d '{
    "name": "production-key",
    "scopes": ["read", "write"],
    "expires_days": 90
  }'
```

Response includes the key (shown only once):
```json
{
  "key": "tenant:sk_live_abc123...",
  "id": "key-uuid",
  "name": "production-key",
  "prefix": "sk_live_abc",
  "scopes": ["read", "write"],
  "expires_at": "2024-06-01T00:00:00Z"
}
```

### Key Scopes

| Scope | Description |
|-------|-------------|
| `read` | Read operations (extract, get schemas) |
| `write` | Write operations (create schemas, start jobs) |
| `delete` | Delete operations |
| `admin` | Administrative operations (team management) |
| `billing` | Billing and subscription management |

### Rate Limits

Default limits per tenant:
- **RPM**: 60 requests per minute
- **RPD**: 1000 requests per day

Rate limit headers in responses:
```
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1234567890
Retry-After: 60
```

---

## API Reference

### Health & Status

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with model status |
| `/ready` | GET | Kubernetes readiness probe |

### OCR Extraction

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ocr/extract` | POST | Synchronous OCR extraction |
| `/ocr/extract/async` | POST | Async extraction with webhook |
| `/ocr/batch` | POST | Batch process from bucket |
| `/ocr/job/{job_id}` | GET | Get job status/results |

### Schema Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/schemas` | GET | List all schemas |
| `/schemas` | POST | Create new schema |
| `/schemas/{id}` | GET | Get schema details |
| `/schemas/{id}` | PUT | Update schema |
| `/schemas/{id}` | DELETE | Delete schema |

### Model Management (BYOM)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/models` | GET | List registered models |
| `/models` | POST | Register new model |
| `/models/{id}` | GET | Get model details |
| `/models/{id}` | PUT | Update model config |
| `/models/{id}` | DELETE | Remove model |
| `/models/{id}/load` | POST | Pre-load model to memory |

### A/B Testing

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ab-tests` | GET | List all tests |
| `/ab-tests` | POST | Create new test |
| `/ab-tests/{id}` | GET | Get test details |
| `/ab-tests/{id}/results` | GET | Get test results |

### API Key Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api-keys` | GET | List API keys |
| `/api-keys` | POST | Create new key |
| `/api-keys/{id}/rotate` | POST | Rotate key |
| `/api-keys/{id}/scopes` | PUT | Update key scopes |
| `/api-keys/{id}/revoke` | POST | Revoke key |

### Team Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/teams` | GET | List user's teams |
| `/teams` | POST | Create new team |
| `/teams/{id}/members` | GET | List team members |
| `/teams/{id}/members/{user_id}` | DELETE | Remove member |
| `/teams/{id}/invitations` | POST | Invite member |
| `/teams/invitations/accept` | POST | Accept invitation |

### Billing

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/billing/customers` | POST | Create Stripe customer |
| `/billing/subscriptions` | POST | Create subscription |
| `/billing/portal` | POST | Get billing portal URL |
| `/billing/invoices/{customer_id}` | GET | Get invoice history |
| `/billing/webhooks/stripe` | POST | Stripe webhook handler |

### Audit Logs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/audit/logs` | GET | Query audit logs |
| `/audit/logs/export` | GET | Export logs (JSON/CSV) |
| `/audit/stats` | GET | Get audit statistics |

---

## Usage Examples

### Basic OCR Extraction

```bash
curl -X POST http://localhost:8080/ocr/extract \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tenant-123:secret" \
  -d '{
    "image_url": "https://example.com/invoice.png"
  }'
```

Response:
```json
{
  "success": true,
  "content": "Invoice #12345\nDate: 2024-01-15\nTotal: $1,234.56",
  "usage": {
    "prompt_tokens": 1200,
    "completion_tokens": 150,
    "total_tokens": 1350
  },
  "model_used": "deepseek-ai/deepseek-vl2-tiny",
  "processing_time_ms": 2340
}
```

### Structured Extraction with Schema

```bash
# Create schema first
curl -X POST http://localhost:8080/schemas \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tenant-123:secret" \
  -d '{
    "name": "invoice",
    "description": "Invoice extraction schema",
    "json_schema": {
      "type": "object",
      "properties": {
        "invoice_number": {"type": "string"},
        "vendor": {"type": "string"},
        "total": {"type": "number"},
        "date": {"type": "string"},
        "line_items": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "description": {"type": "string"},
              "quantity": {"type": "number"},
              "unit_price": {"type": "number"}
            }
          }
        }
      },
      "required": ["invoice_number", "total"]
    }
  }'

# Extract using schema
curl -X POST http://localhost:8080/ocr/extract \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tenant-123:secret" \
  -d '{
    "image_url": "https://example.com/invoice.png",
    "schema_name": "invoice"
  }'
```

Response:
```json
{
  "success": true,
  "content": "...",
  "structured_output": {
    "invoice_number": "INV-2024-001",
    "vendor": "Acme Corp",
    "total": 1234.56,
    "date": "2024-01-15",
    "line_items": [
      {"description": "Widget A", "quantity": 10, "unit_price": 99.99}
    ]
  }
}
```

### Async Extraction with Webhook

```bash
curl -X POST "http://localhost:8080/ocr/extract/async" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tenant-123:secret" \
  -d '{
    "image_url": "https://example.com/large-document.png",
    "webhook_url": "https://my-app.com/webhooks/ocr",
    "schema_name": "invoice"
  }'
```

Response:
```json
{
  "job_id": "job-uuid-123",
  "status": "queued",
  "message": "Job queued for processing"
}
```

### Batch Processing

```bash
curl -X POST http://localhost:8080/ocr/batch \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tenant-123:secret" \
  -d '{
    "source": "s3://my-bucket/invoices/2024/",
    "file_pattern": "*.pdf",
    "schema_name": "invoice",
    "webhook_url": "https://my-app.com/webhooks/batch",
    "output_destination": "s3://my-bucket/results/",
    "max_concurrency": 10
  }'
```

### A/B Testing

```bash
# Create test
curl -X POST http://localhost:8080/ab-tests \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tenant-123:secret" \
  -d '{
    "test_id": "model-comparison-v1",
    "description": "Compare tiny vs small model",
    "variants": [
      {"name": "tiny", "model_name": "deepseek-ai/deepseek-vl2-tiny", "weight": 1},
      {"name": "small", "model_name": "deepseek-ai/deepseek-vl2-small", "weight": 1}
    ]
  }'

# Get results
curl http://localhost:8080/ab-tests/model-comparison-v1/results \
  -H "X-API-Key: tenant-123:secret"
```

### Team Management

```bash
# Create team
curl -X POST http://localhost:8080/teams \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tenant-123:secret" \
  -d '{"name": "Engineering Team"}'

# Invite member
curl -X POST http://localhost:8080/teams/{team_id}/invitations \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tenant-123:secret" \
  -d '{
    "email": "developer@company.com",
    "role": "member"
  }'
```

### Audit Log Query

```bash
# Query recent extractions
curl "http://localhost:8080/audit/logs?action=ocr.extraction_completed&limit=100" \
  -H "X-API-Key: tenant-123:secret"

# Export for compliance
curl "http://localhost:8080/audit/logs/export?format=csv&start_time=2024-01-01T00:00:00Z" \
  -H "X-API-Key: tenant-123:secret" \
  -o audit_export.csv
```

---

## SDKs

### Python SDK

```bash
pip install deepseek-ocr
```

```python
from deepseek_ocr import DeepSeekOCR

client = DeepSeekOCR(
    api_key="tenant:secret",
    base_url="https://api.example.com"
)

# Simple extraction
result = client.extract(image_url="https://example.com/doc.png")
print(result.content)

# With schema
result = client.extract(
    image_path="./invoice.pdf",
    schema_name="invoice"
)
print(result.structured_output)

# Batch processing
job = client.start_batch(
    source="s3://bucket/documents/",
    schema_name="invoice",
    webhook_url="https://app.com/webhook"
)

# Wait for completion
status = client.wait_for_job(job.job_id)
print(f"Processed {status.processed_files} files")
```

See `sdk/python/README.md` for full documentation.

### Node.js SDK

```bash
npm install @deepseek/ocr-sdk
```

```typescript
import { DeepSeekOCR } from '@deepseek/ocr-sdk';

const client = new DeepSeekOCR({
  apiKey: 'tenant:secret',
  baseUrl: 'https://api.example.com',
});

// Simple extraction
const result = await client.extract({
  imageUrl: 'https://example.com/doc.png',
});
console.log(result.content);

// With schema
const structured = await client.extract({
  imageUrl: 'https://example.com/invoice.png',
  schemaName: 'invoice',
});
console.log(structured.structuredOutput);

// Batch processing
const batch = await client.startBatch({
  source: 's3://bucket/documents/',
  schemaName: 'invoice',
  webhookUrl: 'https://app.com/webhook',
});

const status = await client.waitForJob(batch.jobId);
```

See `sdk/nodejs/README.md` for full documentation.

---

## Webhooks

The API sends webhook notifications for async and batch jobs.

### Event Types

#### job.completed
```json
{
  "event": "job.completed",
  "job_id": "uuid",
  "status": "completed",
  "result": {
    "content": "...",
    "structured_output": {...}
  }
}
```

#### job.failed
```json
{
  "event": "job.failed",
  "job_id": "uuid",
  "status": "failed",
  "error": "Error message"
}
```

#### batch.progress
```json
{
  "event": "batch.progress",
  "job_id": "uuid",
  "processed": 50,
  "total": 100,
  "percent": 50.0
}
```

#### batch.completed
```json
{
  "event": "batch.completed",
  "job_id": "uuid",
  "status": "completed",
  "total_files": 100,
  "processed_files": 95,
  "failed_files": 5,
  "result_url": "s3://bucket/results/uuid/"
}
```

### Webhook Security

Webhooks include a signature header for verification:

```
X-Webhook-Signature: sha256=abc123...
```

Verify using your webhook secret:
```python
import hmac
import hashlib

def verify_webhook(payload, signature, secret):
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

---

## Configuration

### Environment Variables

#### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_NAME` | `deepseek-ai/deepseek-vl2-tiny` | VLM model to use |
| `GPU_MEMORY_UTILIZATION` | `0.85` | GPU memory fraction |
| `MAX_MODEL_LEN` | `4096` | Max context length |
| `PORT` | `8080` | API server port |
| `WORKERS` | `1` | Uvicorn workers |

#### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | - | Redis for job tracking and rate limiting |
| `DATABASE_URL` | - | PostgreSQL for schema persistence |

#### Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `STORAGE_BACKEND` | `local` | Storage backend: s3, gcs, local |
| `AWS_ACCESS_KEY_ID` | - | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | - | AWS secret key |
| `AWS_REGION` | `us-east-1` | AWS region |
| `GCS_BUCKET` | - | GCS bucket name |
| `GOOGLE_APPLICATION_CREDENTIALS` | - | GCS credentials path |

#### Billing

| Variable | Default | Description |
|----------|---------|-------------|
| `STRIPE_API_KEY` | - | Stripe secret key |
| `STRIPE_WEBHOOK_SECRET` | - | Stripe webhook signing secret |

#### Security

| Variable | Default | Description |
|----------|---------|-------------|
| `CORS_ORIGINS` | `*` | Allowed CORS origins |
| `RATE_LIMIT_RPM` | `60` | Default requests per minute |
| `RATE_LIMIT_RPD` | `1000` | Default requests per day |

### Model Options

| Model | VRAM | Speed | Quality |
|-------|------|-------|---------|
| `deepseek-ai/deepseek-vl2-tiny` | ~8GB | Fast | Good |
| `deepseek-ai/deepseek-vl2-small` | ~16GB | Medium | Better |
| `deepseek-ai/deepseek-vl2` | ~40GB | Slow | Best |

---

## Deployment

### Pre-download Models for Production

For fast container startup, pre-download models and mount as a volume:

```bash
# Create local cache directory
mkdir -p ./model-cache

# Download model to cache
HF_HOME=./model-cache huggingface-cli download deepseek-ai/deepseek-vl2-tiny

# Run container with mounted cache
docker run -d \
  --gpus all \
  -p 8080:8080 \
  -v $(pwd)/model-cache:/root/.cache/huggingface \
  -e MODEL_NAME=deepseek-ai/deepseek-vl2-tiny \
  deepseek-ocr-api:latest
```

Alternatively, bake models into your Docker image for serverless deployments (increases image size significantly).

### Docker

```bash
# Build image
docker build -f Dockerfile.api -t deepseek-ocr-api:latest .

# Run with GPU (with model cache mounted)
docker run -d \
  --gpus all \
  -p 8080:8080 \
  -v /path/to/model-cache:/root/.cache/huggingface \
  -e MODEL_NAME=deepseek-ai/deepseek-vl2-tiny \
  -e REDIS_URL=redis://redis:6379 \
  -e DATABASE_URL=postgresql://user:pass@db/ocr \
  -e STRIPE_API_KEY=sk_live_xxx \
  deepseek-ocr-api:latest
```

### Google Cloud Run (Recommended)

1. **Configure Terraform**:
```bash
cd infra/cloudrun
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

2. **Build and push container**:
```bash
PROJECT_ID=your-project
REGION=us-central1

# Build
docker build -f Dockerfile.api \
  -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/deepseek-ocr/api:latest .

# Push
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/deepseek-ocr/api:latest
```

3. **Deploy**:
```bash
terraform init
terraform apply
```

### AWS EC2

1. Launch GPU instance (g4dn.xlarge or better)
2. Install NVIDIA drivers and Docker
3. Run container:

```bash
docker run -d \
  --gpus all \
  -p 8080:8080 \
  -e MODEL_NAME=deepseek-ai/deepseek-vl2-tiny \
  -e REDIS_URL=redis://your-elasticache:6379 \
  -e DATABASE_URL=postgresql://user:pass@rds-host/db \
  your-ecr-repo/deepseek-ocr-api:latest
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: deepseek-ocr-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: deepseek-ocr-api
  template:
    metadata:
      labels:
        app: deepseek-ocr-api
    spec:
      containers:
      - name: api
        image: your-registry/deepseek-ocr-api:latest
        ports:
        - containerPort: 8080
        resources:
          limits:
            nvidia.com/gpu: 1
        env:
        - name: MODEL_NAME
          value: deepseek-ai/deepseek-vl2-tiny
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: ocr-secrets
              key: redis-url
```

---

## Administration

### Billing Setup

1. **Create Stripe account** and get API keys
2. **Set environment variables**:
   ```bash
   STRIPE_API_KEY=sk_live_xxx
   STRIPE_WEBHOOK_SECRET=whsec_xxx
   ```
3. **Create products in Stripe** for each plan (Free, Starter, Professional, Enterprise)
4. **Configure webhook endpoint** in Stripe dashboard pointing to `/billing/webhooks/stripe`

### Plans

| Plan | Price | RPM | RPD | Features |
|------|-------|-----|-----|----------|
| Free | $0 | 10 | 100 | Basic extraction |
| Starter | $49/mo | 60 | 1,000 | + Schemas, Async |
| Professional | $199/mo | 300 | 10,000 | + Batch, BYOM |
| Enterprise | Custom | Unlimited | Unlimited | + SLA, Support |

### Team Roles

| Role | Permissions |
|------|-------------|
| Owner | Full access, billing, delete team |
| Admin | Manage members, API keys, schemas |
| Member | Create schemas, run extractions |
| Viewer | Read-only access |

### Audit Compliance

Audit logs track all actions for SOC 2 and HIPAA compliance:

- Authentication events
- Data access and extraction
- Configuration changes
- Billing events
- Team management

Export logs for compliance review:
```bash
curl "http://localhost:8080/audit/logs/export?format=csv" \
  -H "X-API-Key: admin:secret" \
  -o audit_$(date +%Y%m%d).csv
```

---

## Troubleshooting

### Common Issues

#### Model not loading
```
Error: CUDA out of memory
```
**Solution**: Use a smaller model or increase `GPU_MEMORY_UTILIZATION`

#### Rate limit exceeded
```
HTTP 429: Too Many Requests
```
**Solution**: Wait for `Retry-After` seconds or upgrade plan

#### Schema validation failed
```
Error: Output does not match schema
```
**Solution**: Check JSON schema syntax and required fields

#### Webhook not received
**Solution**:
1. Verify webhook URL is accessible
2. Check webhook signature verification
3. Review audit logs for delivery status

### Debugging

Enable debug logging:
```bash
LOG_LEVEL=DEBUG uv run python -m api.main
```

Check job status:
```bash
curl http://localhost:8080/ocr/job/{job_id} \
  -H "X-API-Key: tenant:secret"
```

View rate limit status:
```bash
# Check response headers
curl -v http://localhost:8080/health
# Look for X-RateLimit-* headers
```

### Performance Tuning

1. **Increase GPU memory**: Set `GPU_MEMORY_UTILIZATION=0.9`
2. **Use larger batch sizes**: Set `max_concurrency` in batch requests
3. **Pre-load models**: Call `/models/{id}/load` before high-traffic periods
4. **Scale horizontally**: Deploy multiple instances with load balancer

---

## Roadmap

### Completed

- [x] Real-time OCR extraction
- [x] Async processing with webhooks
- [x] Batch processing from S3/GCS
- [x] Custom JSON schemas
- [x] Multi-tenant isolation
- [x] Redis job tracking
- [x] PostgreSQL persistence
- [x] Rate limiting (RPM/RPD)
- [x] Model A/B testing
- [x] BYOM support
- [x] Python SDK
- [x] Node.js SDK
- [x] Management dashboard
- [x] Stripe billing
- [x] Team management
- [x] API key rotation/scopes
- [x] Audit logging

### Planned

- [ ] Custom model fine-tuning
- [ ] Document preprocessing (PDF to image)
- [ ] Result validation and confidence scores
- [ ] GraphQL API
- [ ] Mobile SDKs (iOS/Android)
- [ ] On-premise deployment option

---

## Support

- **Documentation**: This file and inline code comments
- **Issues**: https://github.com/dickiesanders/VLM-Batch-Deployment/issues

## License

MIT License - see LICENSE file for details.
