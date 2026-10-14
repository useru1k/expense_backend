from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from collections.abc import Iterator


SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    title TEXT NOT NULL,
    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
    transaction_date TEXT NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('income', 'expense')),
    category TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_transactions_owner_date
    ON transactions (owner_id, transaction_date);

CREATE TABLE IF NOT EXISTS budgets (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    category TEXT NOT NULL,
    limit_cents INTEGER NOT NULL CHECK (limit_cents > 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (owner_id, category)
);

CREATE INDEX IF NOT EXISTS idx_budgets_owner
    ON budgets (owner_id);
"""


class Database:
    def __init__(self, database_url: str):
        if not database_url.startswith("sqlite:///"):
            raise ValueError(
                "The first persistence adapter supports sqlite:/// URLs. "
                "Keep the repository interface when adding PostgreSQL."
            )
        raw_path = database_url.removeprefix("sqlite:///")
        self.path = Path(raw_path)
        if not self.path.is_absolute():
            self.path = Path.cwd() / self.path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

