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


class Invoice(BaseModel):
    invoiced_date: str | None = None  # TODO: convert to date
    due_date: str | None = None  # TODO: convert to date
    from_info: Info
    to_info: Info
    amount: Amount
