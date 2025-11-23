import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from api.routes import ocr_router, health_router, schemas_router
from api.routes.ab_testing import router as ab_testing_router
from api.routes.models import router as models_router
from api.routes.billing import router as billing_router
from api.routes.teams import router as teams_router
from api.routes.api_keys import router as api_keys_router
from api.routes.audit import router as audit_router
from api.services.ocr_engine import initialize_engine
from api.services.job_tracker import initialize_job_tracker
from api.services.rate_limiter import initialize_rate_limiter
from api.services.database import initialize_database, get_database
from api.services.billing import initialize_billing

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# OpenAPI tags for documentation
tags_metadata = [
    {
        "name": "Health",
        "description": "Health checks and readiness probes",
    },
    {
        "name": "OCR",
        "description": "Document OCR extraction - sync, async, and batch processing",
    },
    {
        "name": "Schemas",
        "description": "Manage extraction schemas for structured output",
    },
    {
        "name": "Models",
        "description": "BYOM (Bring Your Own Model) - register and manage custom models",
    },
    {
        "name": "A/B Testing",
        "description": "Compare model variants with metrics tracking",
    },
    {
        "name": "API Keys",
        "description": "Create, rotate, and manage API keys with scopes",
    },
    {
        "name": "Teams",
        "description": "Team and organization management with RBAC",
    },
    {
        "name": "Billing",
        "description": "Stripe billing, subscriptions, and usage tracking",
    },
    {
        "name": "Audit",
        "description": "Audit logs for compliance and security",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - initialize services on startup"""
    # Initialize job tracker (Redis or in-memory)
    redis_url = os.getenv("REDIS_URL")
    initialize_job_tracker(redis_url)
    if redis_url:
        logger.info("Initialized Redis job tracker")
    else:
        logger.info("Using in-memory job tracker")

    # Initialize rate limiter
    initialize_rate_limiter(
        redis_url=redis_url,
        requests_per_minute=int(os.getenv("RATE_LIMIT_RPM", "60")),
        requests_per_day=int(os.getenv("RATE_LIMIT_RPD", "1000")),
    )
    logger.info("Initialized rate limiter")

    # Initialize database (PostgreSQL)
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        db = initialize_database(database_url)
        await db.init_db()
        logger.info("Initialized PostgreSQL database")

    # Initialize billing (Stripe)
    stripe_key = os.getenv("STRIPE_API_KEY")
    if stripe_key:
        initialize_billing(stripe_key)
        logger.info("Initialized Stripe billing")

    # Initialize OCR engine
    model_name = os.getenv("MODEL_NAME", "deepseek-ai/deepseek-vl2-tiny")
    gpu_memory_utilization = float(os.getenv("GPU_MEMORY_UTILIZATION", "0.85"))
    max_model_len = int(os.getenv("MAX_MODEL_LEN", "4096"))

    logger.info(f"Initializing OCR engine with model: {model_name}")

    try:
        initialize_engine(
            model_name=model_name,
            gpu_memory_utilization=gpu_memory_utilization,
            max_model_len=max_model_len,
        )
        logger.info("OCR engine initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize OCR engine: {e}")
        # Allow service to start even if model fails to load
        # Health endpoint will report model_loaded=False

    yield

    # Shutdown
    logger.info("Shutting down OCR API")
    db = get_database()
    if db:
        await db.close()


app = FastAPI(
    title="DeepSeek OCR API",
    description="""
## Document OCR and Structured Extraction API

Powered by DeepSeek-VL2 vision-language models via vLLM.

### Features
- **Real-time extraction** - Synchronous OCR with immediate results
- **Structured output** - Custom JSON schemas for data extraction
- **Async processing** - Background jobs with webhook notifications
- **Batch processing** - Process entire S3/GCS buckets
- **BYOM** - Bring Your Own Model from HuggingFace or GCS
- **Rate limiting** - Per-tenant RPM/RPD quotas
- **A/B testing** - Compare model variants with metrics
- **Teams** - Organization management with RBAC
- **Billing** - Stripe integration with usage-based pricing
- **Audit** - Compliance-ready action logging

### Authentication
All endpoints require API key authentication via the `X-API-Key` header:
```
X-API-Key: <tenant_id>:<secret>
```

### Rate Limits
- Default: 60 RPM, 1000 RPD per tenant
- Headers: `X-RateLimit-Remaining`, `Retry-After`
    """,
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=tags_metadata,
    contact={
        "name": "DeepSeek OCR API Support",
        "url": "https://github.com/dickiesanders/VLM-Batch-Deployment",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {"url": "http://localhost:8080", "description": "Local development"},
        {"url": "https://api.example.com", "description": "Production"},
    ],
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with tags
app.include_router(health_router, tags=["Health"])
app.include_router(ocr_router, tags=["OCR"])
app.include_router(schemas_router, tags=["Schemas"])
app.include_router(ab_testing_router, tags=["A/B Testing"])
app.include_router(models_router, tags=["Models"])
app.include_router(billing_router, tags=["Billing"])
app.include_router(teams_router, tags=["Teams"])
app.include_router(api_keys_router, tags=["API Keys"])
app.include_router(audit_router, tags=["Audit"])


@app.get("/")
async def root():
    return {
        "service": "DeepSeek OCR API",
        "version": "1.0.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8080")),
        reload=os.getenv("ENV", "production") == "development",
    )
