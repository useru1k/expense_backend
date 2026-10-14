from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def make_client(tmp_path):
    return TestClient(create_app(f"sqlite:///{tmp_path / 'test.db'}"))


def test_health_and_transaction_crud(tmp_path):
    with make_client(tmp_path) as client:
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


def test_summary_and_budget_conflict(tmp_path):
    with make_client(tmp_path) as client:
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


def test_validation_rejects_invalid_transaction(tmp_path):
    with make_client(tmp_path) as client:
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

