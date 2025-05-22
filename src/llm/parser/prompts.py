QWEN_25_VL_INSTRUCT_PROMPT = (
    "<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n"
    "<|im_start|>user\n<|vision_start|><|image_pad|><|vision_end|>"
    "{instruction}<|im_end|>\n"
    "<|im_start|>assistant\n"
)

INSTRUCTION = """
You are an expert at extracting structured information from invoice images.

Analyze the provided invoice image and extract the following information in JSON format:
- Invoice number
- Invoice date
- Due date
- Vendor information (name, address, phone)
- Customer information (name, address, phone)
- Line items (part numbers, descriptions, quantities, prices)
- Payment information
- Total amounts

IMPORTANT: Extract ONLY the information visible in THIS specific image. Do not include any information from previous images or make assumptions about data not visible in the image.

Return the data in the following JSON format:
{
  "invoice_number": "...",
  "invoiced_date": "...",
  "due_date": "...",
  "from_info": {
    "name": "...",
    "email": "...",
    "phone_number": "...",
    "address": {
      "street": "...",
      "city": "...",
      "state": "...",
      "postal_code": "...",
      "country": "..."
    }
  },
  "to_info": {
    "name": "...",
    "email": "...",
    "phone_number": "...",
    "address": {
      "street": "...",
      "city": "...",
      "state": "...",
      "postal_code": "...",
      "country": "..."
    }
  },
  "line_items": [
    {
      "part_number": "...",
      "description": "...",
      "unit_price": 0.0,
      "quantity": 0,
      "amount": 0.0
    }
  ],
  "payment_method": "...",
  "amount": {
    "sub_total": 0.0,
    "total": 0.0,
    "tax": 0.0,
    "currency": "..."
  }
}
""".strip()
