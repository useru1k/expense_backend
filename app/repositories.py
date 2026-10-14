from __future__ import annotations

import sqlite3
from datetime import date
from typing import Protocol

from .db import Database
from .domain import (
    Budget,
    ConflictError,
    ExpenseCategory,
    NotFoundError,
    Transaction,
    TransactionType,
)


class TransactionRepository(Protocol):
    def list(
        self,
        owner_id: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        transaction_type: TransactionType | None = None,
        category: ExpenseCategory | None = None,
        search: str | None = None,
    ) -> list[Transaction]: ...

    def get(self, owner_id: str, transaction_id: str) -> Transaction: ...

    def create(self, transaction: Transaction) -> Transaction: ...

    def update(self, transaction: Transaction) -> Transaction: ...

    def delete(self, owner_id: str, transaction_id: str) -> None: ...


class BudgetRepository(Protocol):
    def list(self, owner_id: str) -> list[Budget]: ...

    def get_by_category(self, owner_id: str, category: ExpenseCategory) -> Budget | None: ...

    def create(self, budget: Budget) -> Budget: ...

    def update(self, budget: Budget) -> Budget: ...

    def delete(self, owner_id: str, budget_id: str) -> None: ...


class SQLiteTransactionRepository:
    def __init__(self, database: Database):
        self.database = database

    @staticmethod
    def _from_row(row: sqlite3.Row) -> Transaction:
        from .domain import parse_date, parse_datetime

        return Transaction(
            id=row["id"],
            owner_id=row["owner_id"],
            title=row["title"],
            amount_cents=row["amount_cents"],
            date=parse_date(row["transaction_date"]),
            type=TransactionType(row["transaction_type"]),
            category=ExpenseCategory(row["category"]),
            notes=row["notes"],
            created_at=parse_datetime(row["created_at"]),
            updated_at=parse_datetime(row["updated_at"]),
        )

    def list(
        self,
        owner_id: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        transaction_type: TransactionType | None = None,
        category: ExpenseCategory | None = None,
        search: str | None = None,
    ) -> list[Transaction]:
        clauses = ["owner_id = ?"]
        values: list[object] = [owner_id]
        if start_date:
            clauses.append("transaction_date >= ?")
            values.append(start_date.isoformat())
        if end_date:
            clauses.append("transaction_date <= ?")
            values.append(end_date.isoformat())
        if transaction_type:
            clauses.append("transaction_type = ?")
            values.append(transaction_type.value)
        if category:
            clauses.append("category = ?")
            values.append(category.value)
        if search:
            clauses.append("(LOWER(title) LIKE ? OR LOWER(COALESCE(notes, '')) LIKE ?)")
            pattern = f"%{search.lower()}%"
            values.extend([pattern, pattern])

        query = (
            "SELECT * FROM transactions WHERE "
            + " AND ".join(clauses)
            + " ORDER BY transaction_date DESC, created_at DESC"
        )
        with self.database.connect() as connection:
            rows = connection.execute(query, values).fetchall()
        return [self._from_row(row) for row in rows]

    def get(self, owner_id: str, transaction_id: str) -> Transaction:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM transactions WHERE owner_id = ? AND id = ?",
                (owner_id, transaction_id),
            ).fetchone()
        if row is None:
            raise NotFoundError("Transaction not found")
        return self._from_row(row)

    def create(self, transaction: Transaction) -> Transaction:
        with self.database.transaction() as connection:
            connection.execute(
                """INSERT INTO transactions
                (id, owner_id, title, amount_cents, transaction_date,
                 transaction_type, category, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    transaction.id,
                    transaction.owner_id,
                    transaction.title,
                    transaction.amount_cents,
                    transaction.date.isoformat(),
                    transaction.type.value,
                    transaction.category.value,
                    transaction.notes,
                    transaction.created_at.isoformat(),
                    transaction.updated_at.isoformat(),
                ),
            )
        return transaction

    def update(self, transaction: Transaction) -> Transaction:
        with self.database.transaction() as connection:
            result = connection.execute(
                """UPDATE transactions SET title = ?, amount_cents = ?,
                transaction_date = ?, transaction_type = ?, category = ?,
                notes = ?, updated_at = ? WHERE owner_id = ? AND id = ?""",
                (
                    transaction.title,
                    transaction.amount_cents,
                    transaction.date.isoformat(),
                    transaction.type.value,
                    transaction.category.value,
                    transaction.notes,
                    transaction.updated_at.isoformat(),
                    transaction.owner_id,
                    transaction.id,
                ),
            )
        if result.rowcount == 0:
            raise NotFoundError("Transaction not found")
        return transaction

    def delete(self, owner_id: str, transaction_id: str) -> None:
        with self.database.transaction() as connection:
            result = connection.execute(
                "DELETE FROM transactions WHERE owner_id = ? AND id = ?",
                (owner_id, transaction_id),
            )
        if result.rowcount == 0:
            raise NotFoundError("Transaction not found")


class SQLiteBudgetRepository:
    def __init__(self, database: Database):
        self.database = database

    @staticmethod
    def _from_row(row: sqlite3.Row) -> Budget:
        from .domain import parse_datetime

        return Budget(
            id=row["id"],
            owner_id=row["owner_id"],
            category=ExpenseCategory(row["category"]),
            limit_cents=row["limit_cents"],
            created_at=parse_datetime(row["created_at"]),
            updated_at=parse_datetime(row["updated_at"]),
        )

    def list(self, owner_id: str) -> list[Budget]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM budgets WHERE owner_id = ? ORDER BY category",
                (owner_id,),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def get_by_category(self, owner_id: str, category: ExpenseCategory) -> Budget | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM budgets WHERE owner_id = ? AND category = ?",
                (owner_id, category.value),
            ).fetchone()
        return None if row is None else self._from_row(row)

    def create(self, budget: Budget) -> Budget:
        try:
            with self.database.transaction() as connection:
                connection.execute(
                    """INSERT INTO budgets
                    (id, owner_id, category, limit_cents, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        budget.id,
                        budget.owner_id,
                        budget.category.value,
                        budget.limit_cents,
                        budget.created_at.isoformat(),
                        budget.updated_at.isoformat(),
                    ),
                )
        except sqlite3.IntegrityError as error:
            if "UNIQUE" in str(error).upper():
                raise ConflictError("A budget already exists for this category") from error
            raise
        return budget

    def update(self, budget: Budget) -> Budget:
        with self.database.transaction() as connection:
            result = connection.execute(
                """UPDATE budgets SET category = ?, limit_cents = ?, updated_at = ?
                WHERE owner_id = ? AND id = ?""",
                (
                    budget.category.value,
                    budget.limit_cents,
                    budget.updated_at.isoformat(),
                    budget.owner_id,
                    budget.id,
                ),
            )
        if result.rowcount == 0:
            raise NotFoundError("Budget not found")
        return budget

    def delete(self, owner_id: str, budget_id: str) -> None:
        with self.database.transaction() as connection:
            result = connection.execute(
                "DELETE FROM budgets WHERE owner_id = ? AND id = ?",
                (owner_id, budget_id),
            )
        if result.rowcount == 0:
            raise NotFoundError("Budget not found")

