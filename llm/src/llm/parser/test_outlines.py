"""Tuto: https://huggingface.co/learn/cookbook/en/structured_generation_vision_language_models"""

import torch
import outlines
from outlines.models.transformers import Transformers
from outlines.models.transformers_vision import transformers_vision, TransformersVision
from transformers import AutoModelForImageTextToText, AutoProcessor
from PIL import Image

from llm.schemas import StructuredOutputSchema, Invoice
from llm.settings import MODEL_NAME
from llm.prompts import PROMPT


def parse_doc(images: list[Image.Image]):
    model_class, processor_class = get_model_and_processor_class(model_name=MODEL_NAME)
    model = get_vision_model(
        model_name=MODEL_NAME,
        model_class=model_class,
        processor_class=processor_class,
    )
    generator = get_json_generator(model=model, schema=Invoice)
    formatted_prompt = format_prompt(prompt=PROMPT, processor=model.processor)
    return generator(formatted_prompt, images)


def get_model_and_processor_class(model_name: str) -> tuple[str, str]:
    model = AutoModelForImageTextToText.from_pretrained(model_name)
    processor = AutoProcessor.from_pretrained(model_name)
    classes = model.__class__, processor.__class__
    del model, processor
    return classes


def get_vision_model(
    model_name: str,
    model_class: str,
    processor_class: str,
    torch_precision=torch.bfloat16,
) -> TransformersVision:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return transformers_vision(
        model_name,
        model_class=model_class,
        device=device,
        model_kwargs={"torch_dtype": torch_precision, "device_map": "auto"},
        processor_class=processor_class,
    )


def get_json_generator(model: Transformers, schema: StructuredOutputSchema):
    image_data_generator = outlines.generate.json(model, schema)
    return image_data_generator


def format_prompt(prompt: str, processor: AutoProcessor) -> list[dict[str, str]]:
    messages = [
        {
            "role": "user",
            "content": [{"type": "image"}, {"type": "text", "text": prompt}],
        },
    ]
    return processor.apply_chat_template(
        messages,
        add_generation_prompt=True,  # <|im_start|>assistant at the end if True
    )


if __name__ == "__main__":
    from time import time
    from llm.settings import DOCUMENTS_DIR

    timestamp = time()
    images = [Image.open(DOCUMENTS_DIR / "image_0.jpeg").convert("RGB")]
    output = parse_doc(images)
    print(output)
    print("It took: ", time() - timestamp, "secondes.")
