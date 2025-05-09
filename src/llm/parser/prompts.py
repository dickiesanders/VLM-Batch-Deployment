QWEN_25_VL_INSTRUCT_PROMPT = (
    "<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n"
    "<|im_start|>user\n<|vision_start|><|image_pad|><|vision_end|>"
    "{instruction}<|im_end|>\n"
    "<|im_start|>assistant\n"
)

INSTRUCTION = """
Extract the data from this invoice.
Return your response as a valid JSON object.

Here's an example of the expected JSON output: 

{
    "invoiced_date": "21/08/2024",
    "due_date": "21/08/2024",
    "invoice_number": "405027",
    "po_number": "3180",
    "from_info": {
        "name": "Akins Ford Chrysler Dodge Jeep Ram",
        "phone_number": "(770) 867-9137",
        "address": {
            "street": "220 W May St.",
            "city": "Winder, GA",
            "country": "US"
        }
    },
    "to_info": {
        "name": "Allatoona Diesel RT-17",
        "phone_number": "(803) 480-2944",
        "address": {
            "street": "4131 S Main St",
            "city": "Acworth, GA",
            "country": "US"
        }
    },
    "line_items": [
        {
            "part_number": "4C3Z9P456AJ",
            "description": "COOLER - EGR",
            "bin_location": "1030A",
            "unit_price": 347.60,
            "quantity_ordered": 2,
            "quantity_shipped": 0,
            "amount": 0.00
        },
        {
            "part_number": "3C3Z9439AA",
            "description": "GASKET - INTAKE",
            "bin_location": "35D",
            "unit_price": 28.05,
            "quantity_ordered": 1,
            "quantity_shipped": 2,
            "amount": 56.10
        }
        // ...additional items as needed
    ],
    "payment_method": "Credit Cards",
    "amount": {
        "sub_total": 279.01,
        "total": 279.01,
        "vat": 0.0,
        "currency": "USD",
        "core_charge": 30.00,
        "sales_tax": 0.00
    }
}
""".strip()
