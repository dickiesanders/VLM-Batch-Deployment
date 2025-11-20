# DeepSeek OCR API

Real-time document OCR and structured extraction API powered by DeepSeek-VL2 and vLLM.

## Features

- **Real-time extraction**: Synchronous API for immediate results
- **Async processing**: Background jobs with webhook notifications
- **Batch processing**: Process entire S3/GCS buckets
- **Structured output**: Custom JSON schemas for data extraction
- **Multi-tenant**: Schema management with API key authentication
- **Rate limiting**: Per-tenant RPM/RPD quotas
- **A/B testing**: Compare model variants with metrics
- **Cloud-native**: Deploy on Google Cloud Run (GPU) or AWS EC2

## Quick Start

### Local Development

```bash
# Install dependencies
uv sync

# Run the API locally (requires GPU)
MODEL_NAME=deepseek-ai/deepseek-vl2-tiny uv run python -m api.main
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/ready` | GET | Readiness probe |
| `/ocr/extract` | POST | Synchronous OCR extraction |
| `/ocr/extract/async` | POST | Async OCR with webhook support |
| `/ocr/batch` | POST | Batch process from S3/GCS |
| `/ocr/job/{job_id}` | GET | Get job status/results |
| `/schemas` | GET/POST | List/create schemas |
| `/schemas/{id}` | GET/PUT/DELETE | Manage schemas |
| `/models` | GET/POST | List/register models (BYOM) |
| `/models/{id}` | GET/PUT/DELETE | Manage models |
| `/models/{id}/load` | POST | Pre-load model to memory |
| `/ab-tests` | GET/POST | List/create A/B tests |
| `/ab-tests/{id}/results` | GET | Get test results |
| `/api-keys` | GET/POST | List/create API keys |
| `/api-keys/{id}/rotate` | POST | Rotate API key |
| `/api-keys/{id}/revoke` | POST | Revoke API key |
| `/teams` | GET/POST | List/create teams |
| `/teams/{id}/members` | GET | List team members |
| `/teams/{id}/invitations` | POST | Invite member |
| `/billing/customers` | POST | Create Stripe customer |
| `/billing/subscriptions` | POST | Create subscription |
| `/billing/portal` | POST | Billing portal session |
| `/audit/logs` | GET | Query audit logs |
| `/audit/logs/export` | GET | Export audit logs |

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

### Async Extraction with Webhook

```bash
curl -X POST "http://localhost:8080/ocr/extract/async?webhook_url=https://my-app.com/webhook" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tenant-123:secret" \
  -d '{
    "image_url": "https://example.com/invoice.png",
    "output_schema": {
      "type": "object",
      "properties": {
        "invoice_number": {"type": "string"},
        "total": {"type": "number"}
      }
    }
  }'
```

### Batch Processing

```bash
curl -X POST "http://localhost:8080/ocr/batch?webhook_url=https://my-app.com/webhook" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tenant-123:secret" \
  -d '{
    "source_bucket": "my-documents",
    "source_prefix": "invoices/2024/",
    "output_bucket": "my-results",
    "output_prefix": "ocr-output/",
    "output_schema": {
      "type": "object",
      "properties": {
        "invoice_number": {"type": "string"},
        "vendor": {"type": "string"},
        "total": {"type": "number"}
      }
    }
  }'
```

### Schema Management

```bash
# Create schema
curl -X POST http://localhost:8080/schemas \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tenant-123:secret" \
  -d '{
    "name": "Invoice Schema",
    "description": "Standard invoice extraction",
    "json_schema": {
      "type": "object",
      "properties": {
        "invoice_number": {"type": "string"},
        "vendor": {"type": "string"},
        "total": {"type": "number"},
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
      }
    },
    "prompt_template": "Extract invoice data. Pay attention to line items and totals."
  }'

# Use saved schema
curl -X POST http://localhost:8080/ocr/extract \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tenant-123:secret" \
  -d '{
    "image_url": "https://example.com/invoice.png",
    "schema_id": "<schema-id>"
  }'
```

### A/B Testing

```bash
# Create test
curl -X POST http://localhost:8080/ab-tests \
  -H "Content-Type: application/json" \
  -d '{
    "test_id": "model-comparison-v1",
    "description": "Compare tiny vs small model",
    "variants": [
      {"name": "tiny", "model_name": "deepseek-ai/deepseek-vl2-tiny", "weight": 1},
      {"name": "small", "model_name": "deepseek-ai/deepseek-vl2-small", "weight": 1}
    ]
  }'

# Get results
curl http://localhost:8080/ab-tests/model-comparison-v1/results
```

## Webhook Events

The API sends webhook notifications for async/batch jobs:

### Job Completed
```json
{
  "event": "job.completed",
  "job_id": "uuid",
  "status": "completed",
  "result_url": "s3://bucket/results/uuid.json",
  "error": null
}
```

### Batch Progress
```json
{
  "event": "batch.progress",
  "job_id": "uuid",
  "processed": 50,
  "total": 100,
  "percent": 50.0
}
```

## Deployment

### Google Cloud Run (Recommended for Serverless GPU)

1. Configure Terraform:

```bash
cd infra/cloudrun
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

2. Build and push container:

```bash
PROJECT_ID=your-project
REGION=us-central1

docker build -f Dockerfile.api -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/deepseek-ocr-api/api:latest .
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/deepseek-ocr-api/api:latest
```

3. Deploy infrastructure:

```bash
terraform init
terraform apply
```

### AWS EC2 with GPU

```bash
docker run -d \
  --gpus all \
  -p 8080:8080 \
  -e MODEL_NAME=deepseek-ai/deepseek-vl2-tiny \
  -e REDIS_URL=redis://your-redis:6379 \
  -e DATABASE_URL=postgresql://user:pass@host/db \
  your-ecr-repo/deepseek-ocr-api:latest
```

## Configuration

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_NAME` | `deepseek-ai/deepseek-vl2-tiny` | VLM model to use |
| `GPU_MEMORY_UTILIZATION` | `0.85` | GPU memory fraction |
| `MAX_MODEL_LEN` | `4096` | Max context length |
| `PORT` | `8080` | API server port |

### SaaS Features

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | - | Redis for distributed job tracking |
| `DATABASE_URL` | - | PostgreSQL for schema persistence |
| `RATE_LIMIT_RPM` | `60` | Requests per minute per tenant |
| `RATE_LIMIT_RPD` | `1000` | Requests per day per tenant |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |

## Model Options

- `deepseek-ai/deepseek-vl2-tiny` - Fast, lower memory (default)
- `deepseek-ai/deepseek-vl2-small` - Balanced
- `deepseek-ai/deepseek-vl2` - Best quality, requires more VRAM

## Architecture

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

## Rate Limiting

Responses include rate limit headers:

```
X-RateLimit-Remaining: 59
Retry-After: 60
```

When limits are exceeded, returns `429 Too Many Requests`.

## SDKs

### Python SDK

```bash
pip install deepseek-ocr
```

```python
from deepseek_ocr import DeepSeekOCR

client = DeepSeekOCR(api_key="tenant:secret", base_url="https://your-api.com")
result = client.extract(image="invoice.png", schema={"type": "object", ...})
```

See `sdk/python/README.md` for full documentation.

## Dashboard

A Next.js management dashboard is available in `dashboard/`:

```bash
cd dashboard
npm install
npm run dev
```

Features: Schema management, job lookup, BYOM model registration, API key config.

## Roadmap

### Completed
- [x] Batch processing from S3/GCS buckets
- [x] Webhook callbacks for async jobs
- [x] Redis for distributed job tracking
- [x] PostgreSQL for schema persistence
- [x] Rate limiting and usage quotas
- [x] Model A/B testing
- [x] Bring Your Own Model (BYOM) support
- [x] Python SDK
- [x] Management dashboard
- [x] Stripe billing integration
- [x] Team/organization management
- [x] API key rotation and scopes
- [x] Audit logging and compliance
- [x] Node.js SDK

### Planned
- [ ] Custom model fine-tuning
- [ ] Document preprocessing (PDF to image)
- [ ] Result validation and confidence scores
