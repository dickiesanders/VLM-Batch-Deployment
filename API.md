# DeepSeek OCR API

Real-time document OCR and structured extraction API powered by DeepSeek-VL2 and vLLM.

## Features

- **Real-time extraction**: Synchronous API for immediate results
- **Async processing**: Background jobs for large documents
- **Structured output**: Custom JSON schemas for data extraction
- **Multi-tenant**: Schema management with API key authentication
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
| `/ocr/extract` | POST | Synchronous OCR extraction |
| `/ocr/extract/async` | POST | Async OCR extraction |
| `/ocr/job/{job_id}` | GET | Get async job status |
| `/schemas` | GET/POST | List/create schemas |
| `/schemas/{id}` | GET/PUT/DELETE | Manage schemas |

### Example Usage

#### Basic OCR Extraction

```bash
curl -X POST http://localhost:8080/ocr/extract \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tenant-123:secret" \
  -d '{
    "image_url": "https://example.com/invoice.png"
  }'
```

#### Structured Extraction with Inline Schema

```bash
curl -X POST http://localhost:8080/ocr/extract \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tenant-123:secret" \
  -d '{
    "image_url": "https://example.com/invoice.png",
    "output_schema": {
      "type": "object",
      "properties": {
        "invoice_number": {"type": "string"},
        "total": {"type": "number"},
        "date": {"type": "string"}
      }
    }
  }'
```

#### Create and Use Saved Schema

```bash
# Create schema
curl -X POST http://localhost:8080/schemas \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tenant-123:secret" \
  -d '{
    "name": "Invoice Schema",
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
              "amount": {"type": "number"}
            }
          }
        }
      }
    }
  }'

# Use saved schema
curl -X POST http://localhost:8080/ocr/extract \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tenant-123:secret" \
  -d '{
    "image_url": "https://example.com/invoice.png",
    "schema_id": "<schema-id-from-above>"
  }'
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
# Set variables
PROJECT_ID=your-project
REGION=us-central1

# Build and push
docker build -f Dockerfile.api -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/deepseek-ocr-api/api:latest .
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/deepseek-ocr-api/api:latest
```

3. Deploy infrastructure:

```bash
terraform init
terraform apply
```

### AWS EC2 with GPU

1. Launch EC2 instance with NVIDIA GPU (e.g., g4dn.xlarge, g5.xlarge)

2. Install NVIDIA drivers and Docker

3. Run the container:

```bash
docker run -d \
  --gpus all \
  -p 8080:8080 \
  -e MODEL_NAME=deepseek-ai/deepseek-vl2-tiny \
  -e AWS_ACCESS_KEY_ID=xxx \
  -e AWS_SECRET_ACCESS_KEY=xxx \
  your-ecr-repo/deepseek-ocr-api:latest
```

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `MODEL_NAME` | `deepseek-ai/deepseek-vl2-tiny` | VLM model to use |
| `GPU_MEMORY_UTILIZATION` | `0.85` | GPU memory fraction |
| `MAX_MODEL_LEN` | `4096` | Max context length |
| `PORT` | `8080` | API server port |
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
                           ▼
                    ┌─────────────┐
                    │   Storage   │
                    │  (S3/GCS)   │
                    └─────────────┘
```

## Future Enhancements

- [ ] Batch processing from S3/GCS buckets
- [ ] Webhook callbacks for async jobs
- [ ] Redis for distributed job tracking
- [ ] PostgreSQL for schema persistence
- [ ] Rate limiting and usage quotas
- [ ] Model A/B testing
