from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status

from .config import settings
from .domain import ExpenseCategory, TransactionType
from .schemas import (
    BudgetCreate,
    BudgetResponse,
    BudgetUpdate,
    SummaryResponse,
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
)
from .service import ExpenseService


router = APIRouter(prefix="/api/v1")


def get_service(request: Request) -> ExpenseService:
    return request.app.state.expense_service


def get_user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    if x_user_id:
        user_id = x_user_id.strip()
        if user_id:
            return user_id
    if settings.require_user_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-User-Id is required until authentication is configured",
        )
    return settings.default_user_id


def parse_month(month: str | None) -> tuple[int, int]:
    if month is None:
        today = date.today()
        return today.year, today.month
    try:
        parsed = date.fromisoformat(f"{month}-01")
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="month must use YYYY-MM format",
        ) from error
    return parsed.year, parsed.month


def to_transaction_response(transaction) -> TransactionResponse:
    from .domain import cents_to_decimal

    return TransactionResponse(
        id=transaction.id,
        title=transaction.title,
        amount=cents_to_decimal(transaction.amount_cents),
        date=transaction.date,
        type=transaction.type,
        category=transaction.category,
        notes=transaction.notes,
        created_at=transaction.created_at,
        updated_at=transaction.updated_at,
    )


def to_budget_response(budget) -> BudgetResponse:
    from .domain import cents_to_decimal

    return BudgetResponse(
        id=budget.id,
        category=budget.category,
        limit=cents_to_decimal(budget.limit_cents),
        created_at=budget.created_at,
        updated_at=budget.updated_at,
    )


@router.get("/transactions", response_model=list[TransactionResponse])
def list_transactions(
    service: Annotated[ExpenseService, Depends(get_service)],
    user_id: Annotated[str, Depends(get_user_id)],
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    transaction_type: TransactionType | None = Query(default=None, alias="type"),
    category: ExpenseCategory | None = Query(default=None),
    search: str | None = Query(default=None, max_length=120),
) -> list[TransactionResponse]:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must be before end_date")
    transactions = service.list_transactions(
        user_id,
        start_date=start_date,
        end_date=end_date,
        transaction_type=transaction_type,
        category=category,
        search=search,
    )
    return [to_transaction_response(transaction) for transaction in transactions]


@router.post(
    "/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_transaction(
    payload: TransactionCreate,
    service: Annotated[ExpenseService, Depends(get_service)],
    user_id: Annotated[str, Depends(get_user_id)],
) -> TransactionResponse:
    return to_transaction_response(service.create_transaction(user_id, payload))


@router.get("/transactions/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: str,
    service: Annotated[ExpenseService, Depends(get_service)],
    user_id: Annotated[str, Depends(get_user_id)],
) -> TransactionResponse:
    return to_transaction_response(service.get_transaction(user_id, transaction_id))


@router.patch("/transactions/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: str,
    payload: TransactionUpdate,
    service: Annotated[ExpenseService, Depends(get_service)],
    user_id: Annotated[str, Depends(get_user_id)],
) -> TransactionResponse:
    return to_transaction_response(
        service.update_transaction(user_id, transaction_id, payload)
    )


@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: str,
    service: Annotated[ExpenseService, Depends(get_service)],
    user_id: Annotated[str, Depends(get_user_id)],
) -> Response:
    service.delete_transaction(user_id, transaction_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/budgets", response_model=list[BudgetResponse])
def list_budgets(
    service: Annotated[ExpenseService, Depends(get_service)],
    user_id: Annotated[str, Depends(get_user_id)],
) -> list[BudgetResponse]:
    return [to_budget_response(budget) for budget in service.list_budgets(user_id)]


@router.post("/budgets", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
def create_budget(
    payload: BudgetCreate,
    service: Annotated[ExpenseService, Depends(get_service)],
    user_id: Annotated[str, Depends(get_user_id)],
) -> BudgetResponse:
    return to_budget_response(service.create_budget(user_id, payload))


@router.patch("/budgets/{budget_id}", response_model=BudgetResponse)
def update_budget(
    budget_id: str,
    payload: BudgetUpdate,
    service: Annotated[ExpenseService, Depends(get_service)],
    user_id: Annotated[str, Depends(get_user_id)],
) -> BudgetResponse:
    return to_budget_response(service.update_budget(user_id, budget_id, payload))


@router.delete("/budgets/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_id: str,
    service: Annotated[ExpenseService, Depends(get_service)],
    user_id: Annotated[str, Depends(get_user_id)],
) -> Response:
    service.delete_budget(user_id, budget_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/summary", response_model=SummaryResponse)
def get_summary(
    service: Annotated[ExpenseService, Depends(get_service)],
    user_id: Annotated[str, Depends(get_user_id)],
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
) -> SummaryResponse:
    year, month_number = parse_month(month)
    return service.summary(user_id, year, month_number)


