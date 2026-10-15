from __future__ import annotations

import asyncio
from datetime import date
from dataclasses import replace

from app.domain import ExpenseCategory, Transaction, TransactionType, now_utc
from app.repositories import MongoTransactionRepository


class FakeResult:
    def __init__(self, *, matched_count=0, deleted_count=0):
        self.matched_count = matched_count
        self.deleted_count = deleted_count


class FakeCursor:
    def __init__(self, documents):
        self.documents = documents

    def sort(self, _sort):
        return self

    async def to_list(self, _length):
        return list(self.documents.values())


class FakeCollection:
    def __init__(self):
        self.documents = {}

    def find(self, query):
        documents = {
            key: document
            for key, document in self.documents.items()
            if all(document.get(field) == value for field, value in query.items())
        }
        return FakeCursor(documents)

    async def find_one(self, query):
        return next(
            (
                document
                for document in self.documents.values()
                if all(document.get(field) == value for field, value in query.items())
            ),
            None,
        )

    async def insert_one(self, document):
        self.documents[document["_id"]] = document

    async def update_one(self, query, update):
        document = await self.find_one(query)
        if document is None:
            return FakeResult()
        document.update(update["$set"])
        return FakeResult(matched_count=1)

    async def delete_one(self, query):
        document = await self.find_one(query)
        if document is None:
            return FakeResult()
        del self.documents[document["_id"]]
        return FakeResult(deleted_count=1)


def test_mongo_transaction_repository_round_trip():
    async def run():
        repository = MongoTransactionRepository(FakeCollection())
        timestamp = now_utc()
        transaction = Transaction(
            id="transaction-1",
            owner_id="user-a",
            title="Coffee",
            amount_cents=1250,
            date=date(2026, 10, 15),
            type=TransactionType.expense,
            category=ExpenseCategory.dining,
            notes="morning",
            created_at=timestamp,
            updated_at=timestamp,
        )

        await repository.create(transaction)
        stored = await repository.get("user-a", "transaction-1")
        assert stored.amount_cents == 1250
        assert stored.category == ExpenseCategory.dining

        updated = replace(transaction, title="Lunch", updated_at=now_utc())
        await repository.update(updated)
        assert (await repository.get("user-a", "transaction-1")).title == "Lunch"

        await repository.delete("user-a", "transaction-1")
        assert await repository.list("user-a") == []

    asyncio.run(run())

