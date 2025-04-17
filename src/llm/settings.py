from typing import Annotated

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore"
    )  # extra="ignore" for AWS credentials

    # Model config
    model_name: str = "Qwen/Qwen2.5-VL-3B-Instruct"
    gpu_memory_utilisation: Annotated[float, Field(gt=0, le=1)] = 0.9
    max_num_seqs: Annotated[int, Field(gt=0)] = 2
    max_model_len: Annotated[int, Field(multiple_of=8)] = 4096
    max_tokens: Annotated[int, Field(multiple_of=8)] = 2048
    temperature: Annotated[float, Field(ge=0, le=1)] = 0

    # AWS S3
    s3_bucket: str
    s3_preprocessed_images_dir_prefix: str
    s3_processed_dataset_prefix: str


settings = Settings()
