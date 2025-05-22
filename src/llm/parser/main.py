from typing import Any, Type
import json
from io import BytesIO
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
import os

from PIL import Image
import boto3
from botocore.exceptions import ClientError
from vllm import LLM, SamplingParams
from vllm.sampling_params import GuidedDecodingParams
from pydantic import BaseModel
import pandas as pd

from llm.settings import settings
from llm.parser import prompts, schemas

LOGGER = logging.getLogger(__name__)


def main():
    LOGGER.info("Start batch job.")
    LOGGER.info("Start loading images.")
    image_ids, images = load_images(
        s3_bucket=settings.s3_bucket,
        s3_images_folder_uri=settings.s3_preprocessed_images_dir_prefix,
    )
    LOGGER.info("Number of images loaded from S3: %s", len(images))
    LOGGER.info("Start loading model: %s", settings.model_name)
    model, sampling_params = load_model(
        model_name=settings.model_name, schema=schemas.Invoice
    )
    LOGGER.info("Start inference on %s images.", len(images))
    outputs = run_inference(
        model=model,
        sampling_params=sampling_params,
        images=images,
        prompt=prompts.QWEN_25_VL_INSTRUCT_PROMPT.format(
            instruction=prompts.INSTRUCTION
        ),
    )
    del model, sampling_params  # Clear memory
    LOGGER.info("Start structured output extraction.")
    structured_outputs = extract_structured_outputs(outputs=outputs)
    # structured_outputs = validate_structured_outputs(
    #     structured_outputs=structured_outputs,
    # )
    structured_outputs = link_ids_to_data(
        structured_outputs=structured_outputs, ids=image_ids
    )
    LOGGER.info(
        "Start exporting data to Bucket: %s, at %s",
        settings.s3_bucket,
        settings.s3_processed_dataset_prefix,
    )
    with TemporaryDirectory() as temp_dir:
        data_path = Path(temp_dir) / "data.jsonl"
        export_to_jsonl(structured_outputs=structured_outputs, output_path=data_path)
        export_to_s3(data_path=data_path)
    LOGGER.info("Batch job finished succesfully.")


def load_images(
    s3_bucket: str,
    s3_images_folder_uri: str,
) -> tuple[list[str], list[Image.Image]]:
    try:
        s3 = boto3.client("s3")
        response = s3.list_objects_v2(Bucket=s3_bucket, Prefix=s3_images_folder_uri)
        
        if "Contents" not in response:
            LOGGER.error("No objects found in S3 bucket %s with prefix %s", s3_bucket, s3_images_folder_uri)
            return [], []

        images: list[Image.Image] = []
        filenames: list[str] = []

        for obj in response["Contents"]:
            key = obj["Key"]
            # Skip directories or non-image files
            if key.endswith('/') or not any(key.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']):
                LOGGER.info("Skipping non-image file: %s", key)
                continue
                
            LOGGER.info("Attempting to load image: %s", key)
            try:
                response = s3.get_object(Bucket=s3_bucket, Key=key)
                image_data = response["Body"].read()
                
                # Try to open the image and verify it's valid
                try:
                    img = Image.open(BytesIO(image_data))
                    # Force load image data to verify it's valid
                    img.load()
                    images.append(img)
                    filenames.append(key)
                    LOGGER.info("Successfully loaded image: %s, size: %s, format: %s", 
                               key, img.size, img.format)
                except Exception as img_err:
                    LOGGER.error("Failed to process image %s: %s", key, str(img_err))
                    # Optionally save the problematic file for debugging
                    # with open(f"/tmp/debug_{Path(key).name}", "wb") as f:
                    #     f.write(image_data)
            except ClientError as s3_err:
                LOGGER.error("S3 error when loading %s: %s", key, str(s3_err))
        
        # Store the count of contents for the log message
        contents_count = len(response.get("Contents", []))
        LOGGER.info("Successfully loaded %d images out of %d files", 
                   len(images), contents_count)
        return filenames, images
    except ClientError as e:
        LOGGER.error("Issue when loading images from s3: %s.", str(e))
        raise ClientError(str(e)) from e
    except Exception as e:
        LOGGER.error("Something went wrong when loading the images from AWS S3: %s", e)
        raise


def load_model(
    model_name: str, schema: Type[BaseModel] | None
) -> tuple[LLM, SamplingParams]:
    # Use the mounted volume for model cache
    cache_dir = os.environ.get("TRANSFORMERS_CACHE", "/mnt/data/huggingface_cache")
    os.environ["TRANSFORMERS_CACHE"] = cache_dir
    os.environ["HF_HOME"] = os.environ.get("HF_HOME", "/mnt/data/huggingface_home")
    
    # Set Hugging Face token for gated models
    hf_token = os.environ.get("HF_TOKEN") or settings.hf_token
    if hf_token:
        os.environ["HF_TOKEN"] = hf_token
        LOGGER.info("Using Hugging Face token for authentication")
    else:
        LOGGER.warning("No Hugging Face token provided. Gated models may not be accessible.")
    
    # Create cache directories if they don't exist
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    Path(os.environ["HF_HOME"]).mkdir(parents=True, exist_ok=True)
    
    LOGGER.info(f"Using model cache directory: {cache_dir}")
    LOGGER.info(f"Using HF home directory: {os.environ['HF_HOME']}")
    
    # Check available space in the mounted volume
    try:
        import subprocess
        df_output = subprocess.check_output(f"df -h {cache_dir}", shell=True).decode('utf-8')
        LOGGER.info(f"Available space in cache directory:\n{df_output}")
    except Exception as e:
        LOGGER.warning(f"Failed to check disk space: {e}")
    
    llm = LLM(
        model=model_name,
        gpu_memory_utilization=settings.gpu_memory_utilisation,
        max_num_seqs=settings.max_num_seqs,
        max_model_len=settings.max_model_len,
        mm_processor_kwargs={"min_pixels": 28 * 28, "max_pixels": 1280 * 28 * 28},
        disable_mm_preprocessor_cache=True,
        trust_remote_code=True,
        download_dir=cache_dir,
        token=hf_token,  # Pass the token to vLLM
    )
    sampling_params = SamplingParams(
        guided_decoding=GuidedDecodingParams(json=schema.model_json_schema())
        if schema
        else None,
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
    
    # Log the raw outputs
    for i, output in enumerate(outputs):
        LOGGER.info(f"Model output {i} generation stats: tokens={len(output.outputs[0].token_ids)}")
    
    return [output.outputs[0].text for output in outputs]


def extract_structured_outputs(outputs: list[str]) -> list[dict[str, Any]]:
    json_outputs: list[dict[str, Any]] = []
    for i, output in enumerate(outputs):
        LOGGER.info(f"Raw model output {i}: {output[:500]}...")  # Log the first 500 chars of output
        start = output.find("{")
        end = output.rfind("}") + 1  # +1 to include the closing brace
        json_str = output[start:end]
        try:
            parsed_json = json.loads(json_str)
            LOGGER.info(f"Successfully parsed JSON for output {i}")
            json_outputs.append(parsed_json)
        except json.JSONDecodeError as e:
            LOGGER.error(f"Issue with decoding json for LLM output {i}: {e}")
            LOGGER.error(f"JSON string attempted to parse: {json_str[:500]}...")
            json_outputs.append({})
    return json_outputs


def validate_structured_outputs(
    structured_outputs: list[dict[str, Any]],
    # schema: Type[BaseModel] = schemas.BaseModel,
) -> list[dict[str, Any]]:
    """NOTES: Need more work with Pydantic validation.
    There's no feature in Pydantic to return default_value() if not validated.
    """
    pass
    # models = [
    #     schema.model_validate(structured_output).model_dump()
    #     for structured_output in structured_outputs
    # ]
    # return structured_outputs


def link_ids_to_data(
    structured_outputs: list[dict[str, Any]],
    ids: list[str],
) -> list[dict[str, Any]]:
    """After process, link back the ids to data."""
    for output_id, output in zip(ids, structured_outputs):
        output["id"] = output_id
    return structured_outputs


def export_to_parquet(
    structured_outputs: list[dict[str, Any]], output_path: Path
) -> None:
    pd.DataFrame(structured_outputs).to_parquet(output_path)


def export_to_jsonl(
    structured_outputs: list[dict[str, Any]], output_path: Path
) -> None:
    LOGGER.info(f"Exporting {len(structured_outputs)} structured outputs to {output_path}")
    
    with open(output_path, "w") as f:
        for i, item in enumerate(structured_outputs):
            # Add detailed logging to see what's being written
            LOGGER.info(f"Writing output {i} for image ID: {item.get('id', 'unknown')}")
            LOGGER.info(f"Output content preview: {str(item)[:500]}...")
            json.dump(item, f)
            f.write("\n")
    
    # Log the contents of the file for debugging
    LOGGER.info(f"Contents of output file {output_path}:")
    with open(output_path, "r") as f:
        for i, line in enumerate(f):
            LOGGER.info(f"Line {i+1}: {line.strip()[:500]}...")


def export_to_s3(
    data_path: Path,
    s3_bucket: str = settings.s3_bucket,
    s3_processed_dataset_prefix: str = settings.s3_processed_dataset_prefix,
) -> None:
    try:
        s3 = boto3.client("s3")
        s3.upload_file(str(data_path), s3_bucket, s3_processed_dataset_prefix)
    except ClientError as e:
        LOGGER.error("Upload file to S3 failed. Error: %s", str(e))
        raise ClientError(str(e)) from e
