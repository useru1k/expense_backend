from __future__ import annotations

from pymongo import ASCENDING, DESCENDING, AsyncMongoClient, IndexModel
from pymongo.server_api import ServerApi


class MongoDatabase:
    """Owns the Atlas client and creates the indexes used by the API."""

    def __init__(self, uri: str, database_name: str):
        if not uri:
            raise ValueError(
                "MONGODB_URI is not configured. Copy .env.example to .env "
                "and add your MongoDB Atlas connection string."
            )
        self.client = AsyncMongoClient(
            uri,
            server_api=ServerApi("1"),
            tz_aware=True,
        )
        self.database = self.client[database_name]

    @property
    def transactions(self):
        return self.database["transactions"]

    @property
    def budgets(self):
        return self.database["budgets"]

    async def initialize(self) -> None:
        await self.client.admin.command("ping")
        await self.transactions.create_indexes(
            [
                IndexModel(
                    [("owner_id", ASCENDING), ("transaction_date", DESCENDING)],
                    name="transactions_owner_date",
                ),
                IndexModel(
                    [("owner_id", ASCENDING), ("transaction_type", ASCENDING)],
                    name="transactions_owner_type",
                ),
                IndexModel(
                    [("owner_id", ASCENDING), ("category", ASCENDING)],
                    name="transactions_owner_category",
                ),
            ]
        )
        await self.budgets.create_index(
            [("owner_id", ASCENDING), ("category", ASCENDING)],
            name="budgets_owner_category_unique",
            unique=True,
        )

    async def close(self) -> None:
        await self.client.close()

