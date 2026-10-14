from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import router
from .config import settings
from .db import Database
from .domain import ConflictError, NotFoundError
from .repositories import SQLiteBudgetRepository, SQLiteTransactionRepository
from .schemas import HealthResponse
from .service import ExpenseService


def create_app(database_url: str | None = None) -> FastAPI:
    database = Database(database_url or settings.database_url)
    transaction_repository = SQLiteTransactionRepository(database)
    budget_repository = SQLiteBudgetRepository(database)
    service = ExpenseService(transaction_repository, budget_repository)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database.initialize()
        app.state.expense_service = service
        yield

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description=(
            "Backend API for Lumen Finance. Structured financial records are "
            "kept behind repositories so storage can move from SQLite to PostgreSQL."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    @app.exception_handler(NotFoundError)
    async def not_found_handler(_, exception: NotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exception)})

    @app.exception_handler(ConflictError)
    async def conflict_handler(_, exception: ConflictError):
        return JSONResponse(status_code=409, content={"detail": str(exception)})

    @app.get("/health", response_model=HealthResponse, tags=["system"])
    def health() -> HealthResponse:
        return HealthResponse(status="ok", environment=settings.environment)

    return app


app = create_app()

