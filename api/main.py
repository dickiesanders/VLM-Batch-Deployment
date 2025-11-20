import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import ocr_router, health_router, schemas_router
from api.routes.ab_testing import router as ab_testing_router
from api.routes.models import router as models_router
from api.services.ocr_engine import initialize_engine
from api.services.job_tracker import initialize_job_tracker
from api.services.rate_limiter import initialize_rate_limiter
from api.services.database import initialize_database, get_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


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
    Document OCR and structured extraction API powered by DeepSeek-VL2.

    ## Features
    - Real-time document OCR extraction
    - Structured output with custom schemas
    - Async processing for large documents
    - Batch processing from S3/GCS
    - Webhook callbacks
    - Rate limiting and usage quotas
    - Model A/B testing
    - Multi-tenant schema management
    - Bring Your Own Model (BYOM) support
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(ocr_router)
app.include_router(schemas_router)
app.include_router(ab_testing_router)
app.include_router(models_router)


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
