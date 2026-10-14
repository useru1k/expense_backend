from __future__ import annotations

from datetime import date as Date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .domain import ExpenseCategory, TransactionType


Money = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]
OptionalMoney = Annotated[
    Decimal | None, Field(gt=0, max_digits=14, decimal_places=2)
]


class TransactionCreate(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=120)]
    amount: Money
    date: Date
    type: TransactionType
    category: ExpenseCategory
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("title")
    @classmethod
    def title_is_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class TransactionUpdate(BaseModel):
    title: Annotated[str | None, Field(min_length=1, max_length=120)] = None
    amount: OptionalMoney = None
    date: Date | None = None
    type: TransactionType | None = None
    category: ExpenseCategory | None = None
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("title")
    @classmethod
    def title_is_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def must_have_a_change(self) -> "TransactionUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one field is required")
        return self


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    amount: float
    date: Date
    type: TransactionType
    category: ExpenseCategory
    notes: str | None
    created_at: datetime
    updated_at: datetime


class BudgetCreate(BaseModel):
    category: ExpenseCategory
    limit: Money


class BudgetUpdate(BaseModel):
    category: ExpenseCategory | None = None
    limit: OptionalMoney = None

    @model_validator(mode="after")
    def must_have_a_change(self) -> "BudgetUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one field is required")
        return self


class BudgetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    category: ExpenseCategory
    limit: float
    created_at: datetime
    updated_at: datetime


class SummaryResponse(BaseModel):
    month: str
    total_income: float
    total_expenses: float
    balance: float
    total_budget: float
    remaining_budget: float
    category_spending: dict[ExpenseCategory, float]
    weekly_expenses: list[float]
    transaction_count: int


class HealthResponse(BaseModel):
    status: str
    environment: str

