from pydantic import BaseModel, field_validator, ValidationInfo
from typing import List, Optional
import re

class Address(BaseModel):
    street: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None

class Info(BaseModel):
    name: str | None = None
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

class LineItem(BaseModel):
    part_number: str | None = None
    description: str | None = None
    bin_location: str | None = None
    opcode: str | None = None
    unit_price: float | None = None
    labor_cost: float | None = None
    other_cost: float | None = None
    quantity_ordered: int | None = None
    quantity_shipped: int | None = None
    amount: float | None = None

class Amount(BaseModel):
    sub_total: float | None = None
    total: float | None = None
    vat: float | None = None
    currency: str | None = None
    core_charge: float | None = None
    sales_tax: float | None = None
    labor_amount: float | None = None
    misc_charges: float | None = None
    parts_amount: float | None = None

class Invoice(BaseModel):
    invoiced_date: str | None = None
    due_date: str | None = None
    invoice_number: str | None = None
    po_number: str | None = None
    vehicle_info: str | None = None
    from_info: Info
    to_info: Info
    line_items: List[LineItem] | None = None
    payment_method: str | None = None
    amount: Amount
