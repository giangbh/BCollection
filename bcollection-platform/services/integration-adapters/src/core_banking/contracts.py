"""ADP-01 normalized Core snapshot contract, also exposed as JSON Schema."""
from datetime import datetime
from typing import Annotated
from pydantic import BaseModel, Field, field_validator

Money = Annotated[int, Field(strict=True, ge=0)]


class CoreSnapshot(BaseModel):
    loan_id: str = Field(min_length=1)
    debtor_cif: str = Field(min_length=1)
    outstanding_principal: Money
    outstanding_interest: Money
    overdue_amount: Money
    dpd: Annotated[int, Field(strict=True, ge=0)]
    source_version: Annotated[int, Field(strict=True, ge=0)]
    as_of: datetime

    @field_validator("as_of")
    @classmethod
    def timezone_required(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Source timestamp requires timezone")
        return value
