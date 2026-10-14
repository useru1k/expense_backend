from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str
    environment: str
    database_url: str
    cors_origins: tuple[str, ...]
    default_user_id: str
    require_user_header: bool

    @property
    def sqlite_path(self) -> Path:
        """Return the local SQLite path for a sqlite:/// URL."""
        if not self.database_url.startswith("sqlite:///"):
            raise ValueError("sqlite_path is only available for SQLite URLs")

        raw_path = self.database_url.removeprefix("sqlite:///")
        path = Path(raw_path)
        if not path.is_absolute():
            path = Path.cwd() / path
        return path


def load_settings() -> Settings:
    origins = tuple(
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:3000,http://localhost:8080"
        ).split(",")
        if origin.strip()
    )
    return Settings(
        app_name=os.getenv("APP_NAME", "Lumen Finance API"),
        environment=os.getenv("ENVIRONMENT", "development"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./data/expense.db"),
        cors_origins=origins,
        default_user_id=os.getenv("DEFAULT_USER_ID", "demo-user"),
        require_user_header=os.getenv("REQUIRE_USER_HEADER", "false").lower()
        in {"1", "true", "yes", "on"},
    )


settings = load_settings()

