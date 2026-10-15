from __future__ import annotations

import calendar
from datetime import date

from .domain import (
    Budget,
    ExpenseCategory,
    Transaction,
    TransactionType,
    cents_to_decimal,
    decimal_to_cents,
    new_id,
    now_utc,
)
from .repositories import BudgetRepository, TransactionRepository
from .schemas import (
    BudgetCreate,
    BudgetUpdate,
    SummaryResponse,
    TransactionCreate,
    TransactionUpdate,
)


class ExpenseService:
    def __init__(
        self,
        transactions: TransactionRepository,
        budgets: BudgetRepository,
    ):
        self.transactions = transactions
        self.budgets = budgets

    async def list_transactions(
        self,
        owner_id: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        transaction_type: TransactionType | None = None,
        category: ExpenseCategory | None = None,
        search: str | None = None,
    ) -> list[Transaction]:
        return await self.transactions.list(
            owner_id,
            start_date=start_date,
            end_date=end_date,
            transaction_type=transaction_type,
            category=category,
            search=search,
        )

    async def get_transaction(self, owner_id: str, transaction_id: str) -> Transaction:
        return await self.transactions.get(owner_id, transaction_id)

    async def create_transaction(
        self, owner_id: str, payload: TransactionCreate
    ) -> Transaction:
        timestamp = now_utc()
        transaction = Transaction(
            id=new_id(),
            owner_id=owner_id,
            title=payload.title,
            amount_cents=decimal_to_cents(payload.amount),
            date=payload.date,
            type=payload.type,
            category=payload.category,
            notes=payload.notes,
            created_at=timestamp,
            updated_at=timestamp,
        )
        return await self.transactions.create(transaction)

    async def update_transaction(
        self,
        owner_id: str,
        transaction_id: str,
        payload: TransactionUpdate,
    ) -> Transaction:
        current = await self.transactions.get(owner_id, transaction_id)
        fields = payload.model_dump(exclude_unset=True)
        updated = Transaction(
            id=current.id,
            owner_id=current.owner_id,
            title=fields.get("title", current.title),
            amount_cents=(
                decimal_to_cents(fields["amount"])
                if "amount" in fields
                else current.amount_cents
            ),
            date=fields.get("date", current.date),
            type=fields.get("type", current.type),
            category=fields.get("category", current.category),
            notes=fields["notes"] if "notes" in fields else current.notes,
            created_at=current.created_at,
            updated_at=now_utc(),
        )
        return await self.transactions.update(updated)

    async def delete_transaction(self, owner_id: str, transaction_id: str) -> None:
        await self.transactions.delete(owner_id, transaction_id)

    async def list_budgets(self, owner_id: str) -> list[Budget]:
        return await self.budgets.list(owner_id)

    async def create_budget(self, owner_id: str, payload: BudgetCreate) -> Budget:
        timestamp = now_utc()
        budget = Budget(
            id=new_id(),
            owner_id=owner_id,
            category=payload.category,
            limit_cents=decimal_to_cents(payload.limit),
            created_at=timestamp,
            updated_at=timestamp,
        )
        return await self.budgets.create(budget)

    async def update_budget(
        self,
        owner_id: str,
        budget_id: str,
        payload: BudgetUpdate,
    ) -> Budget:
        budgets = await self.budgets.list(owner_id)
        existing = next(
            (budget for budget in budgets if budget.id == budget_id),
            None,
        )
        if existing is None:
            from .domain import NotFoundError

            raise NotFoundError("Budget not found")
        fields = payload.model_dump(exclude_unset=True)
        category = fields.get("category", existing.category)
        if category != existing.category:
            duplicate = await self.budgets.get_by_category(owner_id, category)
            if duplicate is not None and duplicate.id != budget_id:
                from .domain import ConflictError

                raise ConflictError("A budget already exists for this category")
        updated = Budget(
            id=existing.id,
            owner_id=existing.owner_id,
            category=category,
            limit_cents=(
                decimal_to_cents(fields["limit"])
                if "limit" in fields
                else existing.limit_cents
            ),
            created_at=existing.created_at,
            updated_at=now_utc(),
        )
        return await self.budgets.update(updated)

    async def delete_budget(self, owner_id: str, budget_id: str) -> None:
        await self.budgets.delete(owner_id, budget_id)

    async def summary(self, owner_id: str, year: int, month: int) -> SummaryResponse:
        last_day = calendar.monthrange(year, month)[1]
        start = date(year, month, 1)
        end = date(year, month, last_day)
        transactions = await self.list_transactions(
            owner_id, start_date=start, end_date=end
        )
        budgets = await self.list_budgets(owner_id)

        income_cents = sum(
            transaction.amount_cents
            for transaction in transactions
            if transaction.type == TransactionType.income
        )
        expense_cents = sum(
            transaction.amount_cents
            for transaction in transactions
            if transaction.type == TransactionType.expense
        )
        budget_cents = sum(budget.limit_cents for budget in budgets)
        category_cents = {category: 0 for category in ExpenseCategory}
        weekly_cents = [0, 0, 0, 0, 0]
        for transaction in transactions:
            if transaction.type != TransactionType.expense:
                continue
            category_cents[transaction.category] += transaction.amount_cents
            week_index = min((transaction.date.day - 1) // 7, 4)
            weekly_cents[week_index] += transaction.amount_cents

        return SummaryResponse(
            month=f"{year:04d}-{month:02d}",
            total_income=cents_to_decimal(income_cents),
            total_expenses=cents_to_decimal(expense_cents),
            balance=cents_to_decimal(income_cents - expense_cents),
            total_budget=cents_to_decimal(budget_cents),
            remaining_budget=cents_to_decimal(budget_cents - expense_cents),
            category_spending={
                category: cents_to_decimal(amount)
                for category, amount in category_cents.items()
                if amount > 0
            },
            weekly_expenses=[cents_to_decimal(amount) for amount in weekly_cents],
            transaction_count=len(transactions),
        )

