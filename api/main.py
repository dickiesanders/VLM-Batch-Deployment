import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import ocr_router, health_router, schemas_router
from api.services.ocr_engine import initialize_engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - load model on startup"""
    # Startup
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


app = FastAPI(
    title="DeepSeek OCR API",
    description="""
    Document OCR and structured extraction API powered by DeepSeek-VL2.

    ## Features
    - Real-time document OCR extraction
    - Structured output with custom schemas
    - Async processing for large documents
    - Batch processing support
    - S3/GCS storage integration
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
