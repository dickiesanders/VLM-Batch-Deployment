import base64
import json
import logging
from io import BytesIO
from typing import Any, Optional

import httpx
from PIL import Image
from vllm import LLM, SamplingParams
from vllm.sampling_params import GuidedDecodingParams

logger = logging.getLogger(__name__)


class OCREngine:
    """OCR Engine using vLLM with DeepSeek-OCR or similar VLM"""

    def __init__(
        self,
        model_name: str = "deepseek-ai/deepseek-vl2-tiny",
        gpu_memory_utilization: float = 0.85,
        max_model_len: int = 4096,
        max_num_seqs: int = 4,
    ):
        self.model_name = model_name
        self.gpu_memory_utilization = gpu_memory_utilization
        self.max_model_len = max_model_len
        self.max_num_seqs = max_num_seqs
        self._llm: Optional[LLM] = None

    def load_model(self) -> None:
        """Load the VLM model into memory"""
        if self._llm is not None:
            logger.info("Model already loaded")
            return

        logger.info(f"Loading model: {self.model_name}")
        self._llm = LLM(
            model=self.model_name,
            gpu_memory_utilization=self.gpu_memory_utilization,
            max_num_seqs=self.max_num_seqs,
            max_model_len=self.max_model_len,
            trust_remote_code=True,
            mm_processor_kwargs={"min_pixels": 28 * 28, "max_pixels": 1280 * 28 * 28},
        )
        logger.info("Model loaded successfully")

    @property
    def is_loaded(self) -> bool:
        return self._llm is not None

    async def load_image(
        self,
        image_url: Optional[str] = None,
        image_base64: Optional[str] = None,
    ) -> Image.Image:
        """Load image from URL or base64 string"""
        if image_base64:
            image_data = base64.b64decode(image_base64)
            return Image.open(BytesIO(image_data))
        elif image_url:
            async with httpx.AsyncClient() as client:
                response = await client.get(image_url)
                response.raise_for_status()
                return Image.open(BytesIO(response.content))
        else:
            raise ValueError("Either image_url or image_base64 must be provided")

    def extract(
        self,
        image: Image.Image,
        output_schema: Optional[dict[str, Any]] = None,
        prompt: Optional[str] = None,
    ) -> dict[str, Any]:
        """Extract structured data from image"""
        if self._llm is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        # Build prompt
        if prompt is None:
            if output_schema:
                prompt = self._build_structured_prompt(output_schema)
            else:
                prompt = self._build_default_prompt()

        # Configure sampling params
        sampling_params = SamplingParams(
            max_tokens=2048,
            temperature=0.1,
        )

        # Add guided decoding if schema provided
        if output_schema:
            sampling_params.guided_decoding = GuidedDecodingParams(
                json=output_schema
            )

        # Format for DeepSeek-VL2
        formatted_prompt = f"<image>\n{prompt}"

        # Run inference
        inputs = [{
            "prompt": formatted_prompt,
            "multi_modal_data": {"image": image},
        }]

        outputs = self._llm.generate(inputs, sampling_params=sampling_params)
        raw_text = outputs[0].outputs[0].text

        # Parse output
        result = self._parse_output(raw_text, output_schema is not None)
        result["raw_text"] = raw_text

        return result

    def _build_default_prompt(self) -> str:
        return """Extract all text and information from this document image.
Return the extracted content as a JSON object with appropriate fields based on the document type."""

    def _build_structured_prompt(self, schema: dict[str, Any]) -> str:
        schema_str = json.dumps(schema, indent=2)
        return f"""Extract information from this document image according to the following schema:

{schema_str}

Return only valid JSON matching this schema."""

    def _parse_output(self, text: str, expect_json: bool) -> dict[str, Any]:
        """Parse model output into structured data"""
        if not expect_json:
            return {"data": {"text": text}}

        # Try to extract JSON from response
        try:
            # Find JSON in response
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                json_str = text[start:end]
                return {"data": json.loads(json_str)}
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON output: {e}")

        return {"data": {"raw": text}}


# Global engine instance
_engine: Optional[OCREngine] = None


def get_engine() -> OCREngine:
    """Get or create the global OCR engine instance"""
    global _engine
    if _engine is None:
        _engine = OCREngine()
    return _engine


def initialize_engine(
    model_name: str = "deepseek-ai/deepseek-vl2-tiny",
    **kwargs
) -> OCREngine:
    """Initialize the global OCR engine with custom settings"""
    global _engine
    _engine = OCREngine(model_name=model_name, **kwargs)
    _engine.load_model()
    return _engine
