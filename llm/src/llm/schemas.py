from abc import ABC
from datetime import date
from pydantic import BaseModel


class StructuredOutputSchema(BaseModel, ABC):
    pass


class Address(BaseModel):
    street: str | None
    city: str | None
    country: str | None


class Info(BaseModel):
    email: str | None
    phone_number: str | None
    addess: Address


class Amount(BaseModel):
    sub_total: float | None
    total: float | None
    vat: float | None
    currency: str | None


class Invoice(StructuredOutputSchema):
    invoiced_date: date | None
    due_date: date | None
    from_info: Info
    to_info: Info
    amount: Amount
