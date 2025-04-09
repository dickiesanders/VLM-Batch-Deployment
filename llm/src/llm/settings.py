from pathlib import Path

REPO_DIR = Path(__file__).parent.parent.parent
DATASET_PATH = REPO_DIR / "data/hf/data/train-00000-of-00001.parquet"
DOCUMENTS_DIR = REPO_DIR / "data/docs"

MODEL_NAME = "Qwen/Qwen2.5-VL-3B-Instruct"
