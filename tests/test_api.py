from __future__ import annotations

from fastapi.testclient import TestClient

from app.domain import (
    Budget,
    ConflictError,
    ExpenseCategory,
    NotFoundError,
    Transaction,
    TransactionType,
)
from app.main import create_app
from app.service import ExpenseService


class FakeTransactionRepository:
    def __init__(self):
        self.items: dict[str, Transaction] = {}

    async def list(
        self,
        owner_id: str,
        *,
        start_date=None,
        end_date=None,
        transaction_type=None,
        category=None,
        search=None,
    ):
        transactions = [
            transaction
            for transaction in self.items.values()
            if transaction.owner_id == owner_id
            and (start_date is None or transaction.date >= start_date)
            and (end_date is None or transaction.date <= end_date)
            and (transaction_type is None or transaction.type == transaction_type)
            and (category is None or transaction.category == category)
        ]
        if search:
            search = search.lower()
            transactions = [
                transaction
                for transaction in transactions
                if search in transaction.title.lower()
                or search in (transaction.notes or "").lower()
            ]
        return sorted(
            transactions,
            key=lambda transaction: (transaction.date, transaction.created_at),
            reverse=True,
        )

    async def get(self, owner_id: str, transaction_id: str):
        transaction = self.items.get(transaction_id)
        if transaction is None or transaction.owner_id != owner_id:
            raise NotFoundError("Transaction not found")
        return transaction

    async def create(self, transaction: Transaction):
        self.items[transaction.id] = transaction
        return transaction

    async def update(self, transaction: Transaction):
        if transaction.id not in self.items:
            raise NotFoundError("Transaction not found")
        self.items[transaction.id] = transaction
        return transaction

    async def delete(self, owner_id: str, transaction_id: str):
        await self.get(owner_id, transaction_id)
        del self.items[transaction_id]

    async def delete_all(self, owner_id: str):
        self.items = {
            transaction_id: transaction
            for transaction_id, transaction in self.items.items()
            if transaction.owner_id != owner_id
        }


class FakeBudgetRepository:
    def __init__(self):
        self.items: dict[str, Budget] = {}

    async def list(self, owner_id: str):
        return sorted(
            [budget for budget in self.items.values() if budget.owner_id == owner_id],
            key=lambda budget: budget.category.value,
        )

    async def get_by_category(self, owner_id: str, category: ExpenseCategory):
        return next(
            (
                budget
                for budget in self.items.values()
                if budget.owner_id == owner_id and budget.category == category
            ),
            None,
        )

    async def create(self, budget: Budget):
        if await self.get_by_category(budget.owner_id, budget.category):
            raise ConflictError("A budget already exists for this category")
        self.items[budget.id] = budget
        return budget

    async def update(self, budget: Budget):
        if budget.id not in self.items:
            raise NotFoundError("Budget not found")
        self.items[budget.id] = budget
        return budget

    async def delete(self, owner_id: str, budget_id: str):
        budget = self.items.get(budget_id)
        if budget is None or budget.owner_id != owner_id:
            raise NotFoundError("Budget not found")
        del self.items[budget_id]


def make_client():
    service = ExpenseService(FakeTransactionRepository(), FakeBudgetRepository())
    return TestClient(create_app(service=service))


def test_health_and_transaction_crud():
    with make_client() as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        created = client.post(
            "/api/v1/transactions",
            json={
                "title": "Coffee",
                "amount": "12.50",
                "date": "2026-10-14",
                "type": "expense",
                "category": "dining",
                "notes": "with a friend",
            },
            headers={"X-User-Id": "user-a"},
        )
        assert created.status_code == 201
        transaction = created.json()
        assert transaction["amount"] == 12.5
        transaction_id = transaction["id"]

        other_user = client.get(
            "/api/v1/transactions", headers={"X-User-Id": "user-b"}
        )
        assert other_user.status_code == 200
        assert other_user.json() == []

        updated = client.patch(
            f"/api/v1/transactions/{transaction_id}",
            json={"notes": None, "amount": "15.00"},
            headers={"X-User-Id": "user-a"},
        )
        assert updated.status_code == 200
        assert updated.json()["amount"] == 15.0
        assert updated.json()["notes"] is None

        deleted = client.delete(
            f"/api/v1/transactions/{transaction_id}",
            headers={"X-User-Id": "user-a"},
        )
        assert deleted.status_code == 204
        assert client.get(
            f"/api/v1/transactions/{transaction_id}",
            headers={"X-User-Id": "user-a"},
        ).status_code == 404


def test_summary_and_budget_conflict():
    with make_client() as client:
        headers = {"X-User-Id": "user-a"}
        budget = client.post(
            "/api/v1/budgets",
            json={"category": "groceries", "limit": "500.00"},
            headers=headers,
        )
        assert budget.status_code == 201

        duplicate = client.post(
            "/api/v1/budgets",
            json={"category": "groceries", "limit": "650.00"},
            headers=headers,
        )
        assert duplicate.status_code == 409

        for payload in [
            {
                "title": "Salary",
                "amount": "2000.00",
                "date": "2026-10-01",
                "type": "income",
                "category": "other",
            },
            {
                "title": "Market",
                "amount": "125.25",
                "date": "2026-10-08",
                "type": "expense",
                "category": "groceries",
            },
            {
                "title": "Dinner",
                "amount": "40.75",
                "date": "2026-09-30",
                "type": "expense",
                "category": "dining",
            },
        ]:
            assert client.post(
                "/api/v1/transactions", json=payload, headers=headers
            ).status_code == 201

        summary = client.get("/api/v1/summary?month=2026-10", headers=headers)
        assert summary.status_code == 200
        assert summary.json()["total_income"] == 2000.0
        assert summary.json()["total_expenses"] == 125.25
        assert summary.json()["total_budget"] == 500.0
        assert summary.json()["remaining_budget"] == 374.75
        assert summary.json()["category_spending"]["groceries"] == 125.25
        assert summary.json()["transaction_count"] == 2


def test_clear_all_transactions_is_scoped_to_the_owner():
    with make_client() as client:
        for user_id in ["user-a", "user-a", "user-b"]:
            response = client.post(
                "/api/v1/transactions",
                json={
                    "title": "Transaction",
                    "amount": "10.00",
                    "date": "2026-10-15",
                    "type": "expense",
                    "category": "other",
                },
                headers={"X-User-Id": user_id},
            )
            assert response.status_code == 201

        cleared = client.delete(
            "/api/v1/transactions", headers={"X-User-Id": "user-a"}
        )
        assert cleared.status_code == 204
        assert client.get(
            "/api/v1/transactions", headers={"X-User-Id": "user-a"}
        ).json() == []
        assert len(
            client.get(
                "/api/v1/transactions", headers={"X-User-Id": "user-b"}
            ).json()
        ) == 1


def test_validation_rejects_invalid_transaction():
    with make_client() as client:
        response = client.post(
            "/api/v1/transactions",
            json={
                "title": " ",
                "amount": "0",
                "date": "2026-10-14",
                "type": "expense",
                "category": "dining",
            },
        )
        assert response.status_code == 422

