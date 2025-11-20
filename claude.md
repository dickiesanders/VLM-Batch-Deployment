# DeepSeek OCR API - Claude Code Instructions

## Project Overview

Real-time document OCR API using DeepSeek-VL2 via vLLM. Designed as a SaaS solution for structured document extraction.

## Architecture

- **api/**: FastAPI application with OCR endpoints
- **api/services/**: OCR engine (vLLM) and storage backends
- **api/routes/**: API endpoints (ocr, schemas, health)
- **api/models/**: Pydantic schemas
- **infra/cloudrun/**: Terraform for Google Cloud Run GPU deployment
- **src/llm/**: Original batch processing module (reference)

## Key Design Decisions

- **vLLM over Ollama**: Better performance, structured output via GuidedDecoding
- **Multi-tenant**: API key auth with tenant isolation for schemas
- **Storage agnostic**: S3, GCS, and local backends supported
- **Cloud Run primary**: Serverless GPU for cost efficiency

## Development

```bash
# Install deps
uv sync

# Run locally
MODEL_NAME=deepseek-ai/deepseek-vl2-tiny uv run python -m api.main

# Run tests
uv run pytest
```

## Common Tasks

- Add new endpoint: Create in `api/routes/`, register in `api/routes/__init__.py` and `api/main.py`
- Add storage backend: Extend `StorageBackend` in `api/services/storage.py`
- Update models: Edit `api/models/schemas.py` or `api/models/tenant.py`

## Environment Variables

- `MODEL_NAME`: VLM model (default: deepseek-ai/deepseek-vl2-tiny)
- `GPU_MEMORY_UTILIZATION`: GPU memory fraction (default: 0.85)
- `REDIS_URL`: Redis connection for job tracking
- `DATABASE_URL`: PostgreSQL for schema persistence
- `STORAGE_BACKEND`: s3, gcs, or local
