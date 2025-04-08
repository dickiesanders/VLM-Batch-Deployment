import torch
from transformers import (
    LlavaForConditionalGeneration,
)
model_name="mistral-community/pixtral-12b" # original magnet model is able to be loaded without issue
model_class=LlavaForConditionalGeneration

def get_vision_model(model_name: str, model_class: VisionModel):
    model_kwargs = {
        "torch_dtype": torch.bfloat16,
        "attn_implementation": "flash_attention_2",
        "device_map": "auto",
    }
    processor_kwargs = {
        "device": "cuda",
    }

    model = outlines.models.transformers_vision(
        model.model_name,
        model_class=model.model_class,
        model_kwargs=model_kwargs,
        processor_kwargs=processor_kwargs,
    )
    return model
model = get_vision_model(model_name, model_class)