from datetime import date
import re

from pydantic import BaseModel, field_validator, ValidationInfo


class Address(BaseModel):
    street: str | None = None
    city: str | None = None
    country: str | None = None


class Info(BaseModel):
    email: str | None = None
    phone_number: str | None = None
    address: Address

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, email: str | None, info: ValidationInfo) -> str | None:
        if not email:
            return None
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            return cls.model_fields[info.field_name].get_default()
        else:
            return email


class Amount(BaseModel):
    sub_total: float | None = None
    total: float | None = None
    vat: float | None = None
    currency: str | None = None

    # @field_validator("sub_total", "total", "vat", mode="before")
    # @classmethod
    # def validate_amount_fields(cls, value: Any, info: ValidationInfo) -> Any:
    #     if value is None or (isinstance(value, (int, float)) and value < 0):
    #         return cls.model_fields[info.field_name].get_default()
    #     return value

    # @field_validator("currency", mode="before")
    # @classmethod
    # def validate_currency(cls, value: Any) -> Any:
    #     if value == "" or value is None:
    #         return None
    #     return value.upper() if isinstance(value, str) else value


class Invoice(BaseModel):
    invoiced_date: str | None = None  # TODO: convert to date
    due_date: str | None = None  # TODO: convert to date
    from_info: Info
    to_info: Info
    amount: Amount


if __name__ == "__main__":
    invoice_example = {
        "invoiced_date": "20pôlcknck15",
        "due_date": "2023-12-15",
        "from_info": {
            "email": "billing@company.com",
            "phone_number": "+1 (555) 123-4567",
            "address": {
                "street": "123 Business Ave",
                "city": "New York",
                "country": "USA",
            },
        },
        "to_info": {
            "email": "client@example.com",
            "phone_number": "+1 (555) 987-6543",
            "address": {
                "street": "456 Client Street",
                "city": "Boston",
                "country": "USA",
            },
        },
        "amount": {
            "sub_total": 999.99,
            "total": 1179.99,
            "vat": 180.00,
            "currency": "USD",
        },
    }

    invoice = Invoice.model_validate(invoice_example)
    print(invoice)
