"""Extract images from HF datasets"""

from pathlib import Path
from datasets import load_dataset

REPO_DIR = Path(__file__).parent.parent
DATASET_NAME = "mathieu1256/FATURA2-invoices"
DOCUMENTS_DIR = REPO_DIR / "data/docs"


def download_docs(
    dataset_name: str,
    output_path: Path,
    n: int = 10,
) -> None:
    dataset = load_dataset(dataset_name, split="test", keep_in_memory=True)
    for i, image in enumerate(dataset["image"][:n]):
        image.save(output_path / f"image_{i}.jpeg")


if __name__ == "__main__":
    download_docs(dataset_name=DATASET_NAME, output_path=DOCUMENTS_DIR)
