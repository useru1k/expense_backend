from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import router
from .config import settings
from .db import MongoDatabase
from .domain import ConflictError, NotFoundError
from .repositories import MongoBudgetRepository, MongoTransactionRepository
from .schemas import HealthResponse
from .service import ExpenseService


def create_app(*, service: ExpenseService | None = None) -> FastAPI:
    database: MongoDatabase | None = None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        nonlocal database
        if service is None:
            database = MongoDatabase(settings.mongodb_uri, settings.mongodb_database)
            await database.initialize()
            app.state.expense_service = ExpenseService(
                MongoTransactionRepository(database.transactions),
                MongoBudgetRepository(database.budgets),
            )
        else:
            app.state.expense_service = service
        yield
        if database is not None:
            await database.close()

    app = FastAPI(
        title=settings.app_name,
        version="0.2.0",
        description=(
            "Backend API for Lumen Finance using MongoDB Atlas and the "
            "native PyMongo Async driver."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_origin_regex=settings.cors_origin_regex,
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
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", environment=settings.environment)

    return app


app = create_app()

