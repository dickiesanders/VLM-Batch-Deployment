from typing import Any
from datetime import date
from pydantic import BaseModel, field_validator, ValidationInfo, Field


class Address(BaseModel):
    street: str | None = None
    city: str | None = None
    country: str | None = None

    # @field_validator("street", "city", "country", mode="before")
    # @classmethod
    # def validate_string_fields(cls, value: Any, info: ValidationInfo) -> Any:
    #     if value == "" or value is None:
    #         return cls.model_fields[info.field_name].get_default()
    #     return value


class Info(BaseModel):
    email: str | None = None
    phone_number: str | None = None
    address: Address

    # @field_validator("email", "phone_number", mode="before")
    # @classmethod
    # def validate_contact_fields(cls, value: Any, info: ValidationInfo) -> Any:
    #     if value == "" or value is None:
    #         return cls.model_fields[info.field_name].get_default()
    #     return value


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
    invoiced_date: date | None = None
    due_date: date | None = None
    from_info: Info
    to_info: Info
    amount: Amount

    # @field_validator("invoiced_date", "due_date", mode="before")
    # @classmethod
    # def validate_date(cls, value: Any, info: ValidationInfo) -> Any:
    #     if value == "" or value is None:
    #         return cls.model_fields[info.field_name].get_default()
    #     return value


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