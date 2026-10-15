from __future__ import annotations

import re
from datetime import date
from typing import Protocol

from pymongo.errors import DuplicateKeyError

from .domain import (
    Budget,
    ConflictError,
    ExpenseCategory,
    NotFoundError,
    Transaction,
    TransactionType,
)


class TransactionRepository(Protocol):
    async def list(
        self,
        owner_id: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        transaction_type: TransactionType | None = None,
        category: ExpenseCategory | None = None,
        search: str | None = None,
    ) -> list[Transaction]: ...

    async def get(self, owner_id: str, transaction_id: str) -> Transaction: ...

    async def create(self, transaction: Transaction) -> Transaction: ...

    async def update(self, transaction: Transaction) -> Transaction: ...

    async def delete(self, owner_id: str, transaction_id: str) -> None: ...

    async def delete_all(self, owner_id: str) -> None: ...


class BudgetRepository(Protocol):
    async def list(self, owner_id: str) -> list[Budget]: ...

    async def get_by_category(
        self, owner_id: str, category: ExpenseCategory
    ) -> Budget | None: ...

    async def create(self, budget: Budget) -> Budget: ...

    async def update(self, budget: Budget) -> Budget: ...

    async def delete(self, owner_id: str, budget_id: str) -> None: ...


class MongoTransactionRepository:
    def __init__(self, collection):
        self.collection = collection

    @staticmethod
    def _from_document(document) -> Transaction:
        from .domain import parse_date, parse_datetime

        return Transaction(
            id=document["_id"],
            owner_id=document["owner_id"],
            title=document["title"],
            amount_cents=document["amount_cents"],
            date=parse_date(document["transaction_date"]),
            type=TransactionType(document["transaction_type"]),
            category=ExpenseCategory(document["category"]),
            notes=document.get("notes"),
            created_at=parse_datetime(document["created_at"]),
            updated_at=parse_datetime(document["updated_at"]),
        )

    @staticmethod
    def _document(transaction: Transaction) -> dict:
        return {
            "_id": transaction.id,
            "owner_id": transaction.owner_id,
            "title": transaction.title,
            "amount_cents": transaction.amount_cents,
            "transaction_date": transaction.date.isoformat(),
            "transaction_type": transaction.type.value,
            "category": transaction.category.value,
            "notes": transaction.notes,
            "created_at": transaction.created_at,
            "updated_at": transaction.updated_at,
        }

    async def list(
        self,
        owner_id: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        transaction_type: TransactionType | None = None,
        category: ExpenseCategory | None = None,
        search: str | None = None,
    ) -> list[Transaction]:
        query: dict = {"owner_id": owner_id}
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = start_date.isoformat()
            if end_date:
                date_filter["$lte"] = end_date.isoformat()
            query["transaction_date"] = date_filter
        if transaction_type:
            query["transaction_type"] = transaction_type.value
        if category:
            query["category"] = category.value
        if search:
            pattern = re.escape(search.strip())
            query["$or"] = [
                {"title": {"$regex": pattern, "$options": "i"}},
                {"notes": {"$regex": pattern, "$options": "i"}},
            ]

        cursor = self.collection.find(query).sort(
            [("transaction_date", -1), ("created_at", -1)]
        )
        documents = await cursor.to_list(None)
        return [self._from_document(document) for document in documents]

    async def get(self, owner_id: str, transaction_id: str) -> Transaction:
        document = await self.collection.find_one(
            {"_id": transaction_id, "owner_id": owner_id}
        )
        if document is None:
            raise NotFoundError("Transaction not found")
        return self._from_document(document)

    async def create(self, transaction: Transaction) -> Transaction:
        await self.collection.insert_one(self._document(transaction))
        return transaction

    async def update(self, transaction: Transaction) -> Transaction:
        document = self._document(transaction)
        document.pop("_id")
        result = await self.collection.update_one(
            {"_id": transaction.id, "owner_id": transaction.owner_id},
            {"$set": document},
        )
        if result.matched_count == 0:
            raise NotFoundError("Transaction not found")
        return transaction

    async def delete(self, owner_id: str, transaction_id: str) -> None:
        result = await self.collection.delete_one(
            {"_id": transaction_id, "owner_id": owner_id}
        )
        if result.deleted_count == 0:
            raise NotFoundError("Transaction not found")

    async def delete_all(self, owner_id: str) -> None:
        await self.collection.delete_many({"owner_id": owner_id})


class MongoBudgetRepository:
    def __init__(self, collection):
        self.collection = collection

    @staticmethod
    def _from_document(document) -> Budget:
        from .domain import parse_datetime

        return Budget(
            id=document["_id"],
            owner_id=document["owner_id"],
            category=ExpenseCategory(document["category"]),
            limit_cents=document["limit_cents"],
            created_at=parse_datetime(document["created_at"]),
            updated_at=parse_datetime(document["updated_at"]),
        )

    @staticmethod
    def _document(budget: Budget) -> dict:
        return {
            "_id": budget.id,
            "owner_id": budget.owner_id,
            "category": budget.category.value,
            "limit_cents": budget.limit_cents,
            "created_at": budget.created_at,
            "updated_at": budget.updated_at,
        }

    async def list(self, owner_id: str) -> list[Budget]:
        cursor = self.collection.find({"owner_id": owner_id}).sort("category", 1)
        documents = await cursor.to_list(None)
        return [self._from_document(document) for document in documents]

    async def get_by_category(
        self, owner_id: str, category: ExpenseCategory
    ) -> Budget | None:
        document = await self.collection.find_one(
            {"owner_id": owner_id, "category": category.value}
        )
        return None if document is None else self._from_document(document)

    async def create(self, budget: Budget) -> Budget:
        try:
            await self.collection.insert_one(self._document(budget))
        except DuplicateKeyError as error:
            raise ConflictError("A budget already exists for this category") from error
        return budget

    async def update(self, budget: Budget) -> Budget:
        document = self._document(budget)
        document.pop("_id")
        try:
            result = await self.collection.update_one(
                {"_id": budget.id, "owner_id": budget.owner_id},
                {"$set": document},
            )
        except DuplicateKeyError as error:
            raise ConflictError("A budget already exists for this category") from error
        if result.matched_count == 0:
            raise NotFoundError("Budget not found")
        return budget

    async def delete(self, owner_id: str, budget_id: str) -> None:
        result = await self.collection.delete_one(
            {"_id": budget_id, "owner_id": owner_id}
        )
        if result.deleted_count == 0:
            raise NotFoundError("Budget not found")

