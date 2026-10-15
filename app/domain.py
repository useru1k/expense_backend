from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum
from typing import Any
from uuid import uuid4


class TransactionType(StrEnum):
    income = "income"
    expense = "expense"


class ExpenseCategory(StrEnum):
    housing = "housing"
    groceries = "groceries"
    dining = "dining"
    transport = "transport"
    shopping = "shopping"
    health = "health"
    subscriptions = "subscriptions"
    entertainment = "entertainment"
    other = "other"


def new_id() -> str:
    return str(uuid4())


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def decimal_to_cents(value: Decimal) -> int:
    quantized = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(quantized * 100)


def cents_to_decimal(value: int) -> Decimal:
    return (Decimal(value) / Decimal(100)).quantize(Decimal("0.01"))


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def parse_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


@dataclass(frozen=True)
class Transaction:
    id: str
    owner_id: str
    title: str
    amount_cents: int
    date: date
    type: TransactionType
    category: ExpenseCategory
    notes: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class Budget:
    id: str
    owner_id: str
    category: ExpenseCategory
    limit_cents: int
    created_at: datetime
    updated_at: datetime


class DomainError(Exception):
    """Base class for expected application errors."""


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    pass


def transaction_to_dict(transaction: Transaction) -> dict[str, Any]:
    return {
        "id": transaction.id,
        "owner_id": transaction.owner_id,
        "title": transaction.title,
        "amount_cents": transaction.amount_cents,
        "date": transaction.date.isoformat(),
        "type": transaction.type.value,
        "category": transaction.category.value,
        "notes": transaction.notes,
        "created_at": transaction.created_at.isoformat(),
        "updated_at": transaction.updated_at.isoformat(),
    }

