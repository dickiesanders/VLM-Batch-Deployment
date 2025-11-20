# DeepSeek OCR Python SDK

Official Python SDK for the DeepSeek OCR API.

## Installation

```bash
pip install deepseek-ocr
```

## Quick Start

```python
from deepseek_ocr import DeepSeekOCR

# Initialize client
client = DeepSeekOCR(
    api_key="your-tenant-id:your-secret-key",
    base_url="https://your-api-url.com"
)

# Extract text from image URL
result = client.extract(image_url="https://example.com/invoice.png")
print(result.result.data)

# Extract with structured output
schema = {
    "type": "object",
    "properties": {
        "invoice_number": {"type": "string"},
        "total": {"type": "number"},
        "vendor": {"type": "string"}
    }
}
result = client.extract(
    image_url="https://example.com/invoice.png",
    schema=schema
)
print(result.result.data)
```

## Features

### Extract from Local File

```python
result = client.extract(image="path/to/invoice.png")
```

### Use Saved Schema

```python
# Create a reusable schema
schema = client.create_schema(
    name="Invoice Schema",
    json_schema={
        "type": "object",
        "properties": {
            "invoice_number": {"type": "string"},
            "total": {"type": "number"}
        }
    }
)

# Use it for extraction
result = client.extract(
    image_url="https://example.com/invoice.png",
    schema_id=schema.id
)
```

### Async Extraction with Polling

```python
# Start async job
job_id = client.extract_async(image_url="https://example.com/large-doc.png")

# Wait for completion
result = client.wait_for_job(job_id, poll_interval=2.0, timeout=300.0)
print(result.result.data)
```

### Batch Processing

```python
# Process all images in S3 bucket
job_id = client.batch(
    source_bucket="my-documents",
    source_prefix="invoices/2024/",
    output_bucket="my-results",
    output_prefix="ocr-output/",
    schema=schema,
    webhook_url="https://my-app.com/webhook"
)
```

### Custom Models (BYOM)

```python
# Register a custom HuggingFace model
model = client.register_model(
    name="my-fine-tuned-ocr",
    source="huggingface",
    model_id="myorg/custom-vlm",
    hf_token="hf_xxx",
    gpu_memory_utilization=0.8,
    max_model_len=8192
)

# Use custom model for extraction
result = client.extract(
    image_url="https://example.com/invoice.png",
    model_id=model.id
)
```

### Async Client

```python
import asyncio
from deepseek_ocr import AsyncDeepSeekOCR

async def main():
    async with AsyncDeepSeekOCR(api_key="your-key") as client:
        result = await client.extract(
            image_url="https://example.com/invoice.png"
        )
        print(result.result.data)

asyncio.run(main())
```

## API Reference

### DeepSeekOCR

#### OCR Methods
- `extract()` - Synchronous extraction
- `extract_async()` - Start async job
- `get_job()` - Get job status
- `wait_for_job()` - Poll until complete
- `batch()` - Batch processing

#### Schema Methods
- `create_schema()` - Create new schema
- `list_schemas()` - List all schemas
- `get_schema()` - Get schema by ID
- `delete_schema()` - Delete schema

#### Model Methods (BYOM)
- `register_model()` - Register custom model
- `list_models()` - List registered models
- `delete_model()` - Delete model
- `load_model()` - Pre-load model

#### Utilities
- `health()` - Check API health

## Error Handling

```python
import httpx

try:
    result = client.extract(image_url="https://example.com/invoice.png")
except httpx.HTTPStatusError as e:
    if e.response.status_code == 429:
        print("Rate limit exceeded")
    elif e.response.status_code == 404:
        print("Resource not found")
    else:
        print(f"API error: {e.response.text}")
```

## Configuration

```python
client = DeepSeekOCR(
    api_key="tenant:secret",
    base_url="https://api.deepseek-ocr.com",
    timeout=120.0  # seconds
)
```

## License

MIT
