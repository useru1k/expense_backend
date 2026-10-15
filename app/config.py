from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote_plus, unquote

from dotenv import load_dotenv


load_dotenv()


def normalize_mongodb_uri(uri: str) -> str:
    """Escape Atlas username/password characters without exposing credentials."""
    if "://" not in uri or "@" not in uri:
        return uri

    scheme, remainder = uri.split("://", 1)
    userinfo, authority = remainder.rsplit("@", 1)
    if ":" not in userinfo:
        return uri

    username, password = userinfo.split(":", 1)
    escaped_username = quote_plus(unquote(username))
    escaped_password = quote_plus(unquote(password))
    return f"{scheme}://{escaped_username}:{escaped_password}@{authority}"


@dataclass(frozen=True)
class Settings:
    app_name: str
    environment: str
    mongodb_uri: str
    mongodb_database: str
    cors_origins: tuple[str, ...]
    cors_origin_regex: str
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
        mongodb_uri=normalize_mongodb_uri(os.getenv("MONGODB_URI", "")),
        mongodb_database=os.getenv("MONGODB_DATABASE", "lumen_finance"),
        cors_origins=origins,
        cors_origin_regex=os.getenv(
            "CORS_ORIGIN_REGEX",
            r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
        ),
        default_user_id=os.getenv("DEFAULT_USER_ID", "demo-user"),
        require_user_header=os.getenv("REQUIRE_USER_HEADER", "false").lower()
        in {"1", "true", "yes", "on"},
    )


settings = load_settings()

