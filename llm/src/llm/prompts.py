PROMPT = """
You are responsible of extracting data from invoice documents.
Here are some informations about the data you need to extract:

Dates:
    * invoiced_date: The date when the invoice was issued (format: YYYY-MM-DD)
    * due_date: The payment due date (format: YYYY-MM-DD)

Sender and Recipient Information:
    * email: email address
    * phone_number: contact phone number

Address:
    * street: Street address
    * city: city
    * country: country in 2 letters (US, FR, SP, etc...)

Financial Amounts:

    * sub_total: Amount before taxes
    * total: Final amount to pay (including taxes)
    * vat: VAT/tax amount (if specified separately)
    * currency: Currency code (e.g., USD, EUR, GBP)

---

Addtional instructions:
    * Mark fields as null if they cannot be found in the document
    * Normalize all dates to ISO format (YYYY-MM-DD)
    * Extract currency symbols (€, $, £) and convert to standard currency codes
    * Handle both numerical and written amounts (e.g., "100" vs "one hundred")
    * Preserve decimal points for monetary values when present
    * Normalize phone numbers to international format when possible

Return your response as a valid JSON object.
""".strip()
