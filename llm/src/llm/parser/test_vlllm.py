from PIL import Image

from vllm import LLM, SamplingParams
from vllm.sampling_params import GuidedDecodingParams

from llm.settings import MODEL_NAME, DOCUMENTS_DIR
from llm.prompts import QWEN_25_VL_7B_INSTRUCT_PROMPT, INSTRUCTION
from llm.schemas import Invoice

images = [Image.open(DOCUMENTS_DIR / "image_0.jpeg").convert("RGB")]

llm = LLM(
    model=MODEL_NAME,
    gpu_memory_utilization=0.9,
    max_num_seqs=4,
    max_model_len=4096,
)

json_schema = Invoice.model_json_schema()

guided_decoding_params = GuidedDecodingParams(json=json_schema)
sampling_params = SamplingParams(
    # guided_decoding=guided_decoding_params,
    max_tokens=4096,
)

formatted_prompt = QWEN_25_VL_7B_INSTRUCT_PROMPT.format(instruction=INSTRUCTION)

print(formatted_prompt)

inputs = [
    {
        "prompt": formatted_prompt,
        "multi_modal_data": {"image": image},
        "sampling_params": sampling_params,
    }
    for image in images
]

outputs = llm.generate(inputs)

print(outputs[0].outputs[0].text)
