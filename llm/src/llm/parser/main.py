from typing import Any, Type
import json
from io import BytesIO
import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image
import boto3
from botocore.exceptions import ClientError
from vllm import LLM, SamplingParams
from pydantic import BaseModel
import pandas as pd

from llm.settings import settings
from llm.parser import prompts, schemas

LOGGER = logging.getLogger(__name__)


def main():
    LOGGER.info("Start batch job.")
    LOGGER.info("Start loading images.")
    images = load_images(
        s3_bucket=settings.s3_bucket,
        s3_images_folder_uri=settings.s3_preprocessed_images_dir_prefix,
    )
    LOGGER.info("Start loading model: %s", settings.model_name)
    model, sampling_params = load_model(model_name=settings.model_name)
    LOGGER.info("Start inference on %s images.", len(images))
    outputs = run_inference(
        model=model,
        sampling_params=sampling_params,
        images=images,
        prompt=prompts.QWEN_25_VL_INSTRUCT_PROMPT.format(prompts.INSTRUCTION),
    )
    LOGGER.info("Start structured output extraction.")
    structured_outputs = extract_structured_outputs(outputs=outputs)
    data_models = validate_structured_outputs(
        structured_outputs=structured_outputs, schema=schemas.Invoice
    )
    LOGGER.info(
        "Start exporting data to Bucket: %s, at %s",
        settings.s3_bucket,
        settings.s3_processed_parquet_prefix,
    )
    with TemporaryDirectory() as temp_dir:
        parquet_path = Path(temp_dir) / "data.parquet"
        export_to_parquet(models=data_models, output_path=parquet_path)
        export_to_s3(parquet_path=parquet_path)
    LOGGER.info("Batch job finished succesfully.")


def load_images(
    s3_bucket: str,
    s3_images_folder_uri: str,
) -> list[Image.Image]:
    try:
        s3 = boto3.client("s3")
        response = s3.list_objects_v2(Bucket=s3_bucket, Prefix=s3_images_folder_uri)
        images: list[Image.Image] = []
        for obj in response["Contents"]:
            key = obj["Key"]
            response = s3.get_object(Bucket=s3_bucket, Key=key)
            image_data = response["Body"].read()
            images.append(Image.open(BytesIO(image_data)))
        return images
    except ClientError as e:
        LOGGER.error("Issue when loading images from s3: %s.", str(e))
        raise ClientError(str(e)) from e


def load_model(model_name: str) -> tuple[LLM, SamplingParams]:
    llm = LLM(
        model=model_name,
        gpu_memory_utilization=settings.gpu_memory_utilisation,
        max_num_seqs=settings.max_num_seqs,
        max_model_len=settings.max_model_len,
        mm_processor_kwargs={"min_pixels": 28 * 28, "max_pixels": 1280 * 28 * 28},
        disable_mm_preprocessor_cache=True,
    )
    sampling_params = SamplingParams(
        max_tokens=settings.max_tokens,
        temperature=settings.temperature,
    )
    return llm, sampling_params


def run_inference(
    model: LLM, sampling_params: SamplingParams, images: list[Image.Image], prompt: str
) -> list[str]:
    """Generate text output for each image"""
    inputs = [
        {
            "prompt": prompt,
            "multi_modal_data": {"image": image},
        }
        for image in images
    ]
    outputs = model.generate(inputs, sampling_params=sampling_params)
    del model  # clear memory
    return [output.outputs[0].text for output in outputs]


def extract_structured_outputs(outputs: list[str]) -> list[dict[str, Any]]:
    json_outputs: list[dict[str, Any]] = []
    for output in outputs:
        start = output.find("{")
        end = output.rfind("}") + 1  # +1 to include the closing brace
        json_str = output[start:end]
        try:
            json_outputs.append(json.loads(json_str))
        except json.JSONDecodeError as e:
            LOGGER.error("Issue with decoding json for LLM output: %s", e)
            json_outputs.append({})
    return json_outputs


def validate_structured_outputs(
    structured_outputs: list[dict[str, Any]],
    schema: Type[BaseModel] = schemas.BaseModel,
) -> list[BaseModel]:
    models = [
        schema.model_validate(structured_output)
        for structured_output in structured_outputs
    ]
    return models


def export_to_parquet(models: list[BaseModel], output_path: Path) -> None:
    dicts = [model.model_dump() for model in models]
    pd.DataFrame(dicts).to_parquet(output_path)


def export_to_s3(
    parquet_path: Path,
    s3_bucket: str = settings.s3_bucket,
    s3_processed_parquet_prefix: str = settings.s3_processed_parquet_prefix,
) -> None:
    if parquet_path.suffix != ".parquet":
        LOGGER.error(
            "Wrong processed dataset format. Current format: %s", str(parquet_path)
        )
        raise ValueError
    try:
        s3 = boto3.client("s3")
        s3.upload_file(str(parquet_path), s3_bucket, s3_processed_parquet_prefix)
    except ClientError as e:
        LOGGER.error("Upload file to S3 failed. Error: %s", str(e))
        raise ClientError(str(e)) from e
