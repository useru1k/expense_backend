from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str
    environment: str
    mongodb_uri: str
    mongodb_database: str
    cors_origins: tuple[str, ...]
    default_user_id: str
    require_user_header: bool


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
        mongodb_uri=os.getenv("MONGODB_URI", ""),
        mongodb_database=os.getenv("MONGODB_DATABASE", "lumen_finance"),
        cors_origins=origins,
        default_user_id=os.getenv("DEFAULT_USER_ID", "demo-user"),
        require_user_header=os.getenv("REQUIRE_USER_HEADER", "false").lower()
        in {"1", "true", "yes", "on"},
    )


settings = load_settings()

