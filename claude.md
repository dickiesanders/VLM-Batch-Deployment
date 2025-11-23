# DeepSeek OCR API - Claude Code Instructions

## Project Overview

Real-time document OCR API using DeepSeek-VL2 via vLLM. Full SaaS solution with billing, teams, BYOM support, and multi-tenant isolation.

## Architecture

```
├── api/
│   ├── main.py              # FastAPI app entry point
│   ├── routes/              # API endpoints
│   │   ├── ocr.py           # OCR extraction endpoints
│   │   ├── schemas.py       # Schema management
│   │   ├── models.py        # BYOM model registry
│   │   ├── ab_testing.py    # A/B test management
│   │   ├── billing.py       # Stripe billing
│   │   ├── teams.py         # Team management
│   │   ├── api_keys.py      # API key management
│   │   └── audit.py         # Audit logging
│   ├── services/
│   │   ├── ocr_engine.py    # vLLM OCR processing
│   │   ├── storage.py       # S3/GCS/local backends
│   │   ├── rate_limiter.py  # RPM/RPD rate limiting
│   │   ├── billing.py       # Stripe integration
│   │   ├── teams.py         # Team/org management
│   │   ├── api_keys.py      # Key generation/rotation
│   │   ├── audit.py         # Audit logging
│   │   └── model_registry.py # BYOM registry
│   └── models/              # Pydantic schemas
├── sdk/
│   ├── python/              # Python SDK
│   └── nodejs/              # Node.js/TypeScript SDK
├── dashboard/               # Next.js management UI
├── infra/cloudrun/          # Terraform deployment
└── tests/services/          # Pytest test suite
```

## Key Design Decisions

- **vLLM over Ollama**: Better performance, structured output via GuidedDecoding
- **Multi-tenant**: API key auth with tenant isolation
- **Storage agnostic**: S3, GCS, and local backends
- **Cloud Run primary**: Serverless GPU for cost efficiency
- **Stripe billing**: Usage-based metered billing
- **RBAC teams**: Owner > Admin > Member > Viewer permissions
- **Multi-model support**: HuggingFace, GCS, local, external sources
- **GCS model cache**: BYOM models downloaded on-demand from GCS

## Multi-Model Architecture

Model sources supported:
- `huggingface` - HuggingFace Hub (default)
- `gcs` - Google Cloud Storage (for BYOM)
- `local` - Local file path
- `external` - Third-party API endpoints

Cloud Run patterns:
1. **Single model** - Bake into image (~10GB)
2. **Multiple services** - One service per model, route by parameter
3. **GCS cache** - Download from GCS on first use, cache locally

Key files:
- `api/services/model_registry.py` - Model registration and loading
- `ModelLoader` class handles GCS/HF downloads
- `ModelRegistry.get_engine()` loads models on-demand
- `ModelRegistry.preload_model()` pre-downloads without loading to GPU

## Development

```bash
# Install deps
uv sync

# Run locally (requires GPU)
MODEL_NAME=deepseek-ai/deepseek-vl2-tiny uv run python -m api.main

# Run tests
uv sync --group dev
uv run pytest tests/ -v

# Run specific test
uv run pytest tests/services/test_api_keys.py -v
```

## Common Tasks

### Add new endpoint
1. Create route in `api/routes/new_route.py`
2. Register router in `api/main.py`: `app.include_router(new_router)`

### Add storage backend
Extend `StorageBackend` in `api/services/storage.py`

### Add new service
1. Create service in `api/services/new_service.py`
2. Add tests in `tests/services/test_new_service.py`
3. Create route if needed

### Update billing plans
Modify `Plan` enum and `PLAN_PRICES` in `api/services/billing.py`

## Environment Variables

### Core
- `MODEL_NAME`: VLM model (default: deepseek-ai/deepseek-vl2-tiny)
- `GPU_MEMORY_UTILIZATION`: GPU memory fraction (default: 0.85)
- `MAX_MODEL_LEN`: Max context length (default: 4096)
- `PORT`: Server port (default: 8080)

### Database
- `REDIS_URL`: Redis for job tracking and rate limiting
- `DATABASE_URL`: PostgreSQL for schema persistence

### Storage
- `STORAGE_BACKEND`: s3, gcs, or local
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`: For S3
- `GOOGLE_APPLICATION_CREDENTIALS`: For GCS

### Models
- `MODEL_CACHE_DIR`: Local cache for downloaded models (default: /tmp/model-cache)
- `GCS_MODELS_BUCKET`: Default GCS bucket for BYOM uploads
- `PRELOAD_MODELS`: Comma-separated model IDs to preload on startup

### Billing
- `STRIPE_API_KEY`: Stripe secret key
- `STRIPE_WEBHOOK_SECRET`: Webhook signing secret

### Security
- `CORS_ORIGINS`: Allowed origins (default: *)
- `RATE_LIMIT_RPM`: Requests per minute (default: 60)
- `RATE_LIMIT_RPD`: Requests per day (default: 1000)

## Testing

Tests use pytest with async support. Services are tested with mocks for external dependencies (Stripe, Redis).

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=api --cov-report=html
```

## Deployment

See `infra/cloudrun/` for Terraform configuration. Key steps:
1. Build Docker image with `Dockerfile.api`
2. Push to Artifact Registry
3. Run `terraform apply`

## API Key Format

API keys follow the format: `tenant_id:secret`
- Parsed from `X-API-Key` header
- Secrets are hashed with SHA-256 for storage
- Keys have scopes: read, write, delete, admin, billing
