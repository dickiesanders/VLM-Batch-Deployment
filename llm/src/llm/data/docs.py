"""Extract images from HF datasets"""

from pathlib import Path
from datasets import Dataset


def extract_images_from_dataset(
    dataset_path: Path,
    output_path: Path,
    n: int = 10,
) -> None:
    dataset = Dataset.from_parquet(str(dataset_path)).shuffle()
    for i, image in enumerate(dataset["image"][:n]):
        image.save(output_path / f"image_{i}.jpeg")


if __name__ == "__main__":
    from llm.settings import DATASET_PATH, DOCUMENTS_DIR

    extract_images_from_dataset(dataset_path=DATASET_PATH, output_path=DOCUMENTS_DIR)
