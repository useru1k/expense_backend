# Lumen Finance API

This is the backend for the Flutter expense tracker. It provides a FastAPI HTTP API, MongoDB Atlas persistence through the native PyMongo Async driver, input validation, owner-scoped records, and calculated monthly summaries.

The code separates the business service from the MongoDB repository adapter. Transactions and budgets are stored in separate MongoDB collections, with indexes created automatically during application startup.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and replace <db_password> with the password for the Atlas user.
python -m app
```

The API is available at `http://127.0.0.1:8000`. Interactive documentation is at `/docs`.

Run checks with:

```powershell
python -m pytest
```

## API surface

- `GET /health`
- `GET /api/v1/transactions`
- `POST /api/v1/transactions`
- `GET /api/v1/transactions/{id}`
- `PATCH /api/v1/transactions/{id}`
- `DELETE /api/v1/transactions/{id}`
- `DELETE /api/v1/transactions` (delete all transactions for the current user)
- `GET /api/v1/budgets`
- `POST /api/v1/budgets`
- `PATCH /api/v1/budgets/{id}`
- `DELETE /api/v1/budgets/{id}`
- `GET /api/v1/summary?month=YYYY-MM`

Until authentication is added, records are scoped by the `X-User-Id` header. In development it defaults to `demo-user`; set `REQUIRE_USER_HEADER=true` before exposing the service anywhere shared. This header is only a development boundary, not an authentication system.

Amounts are stored as integer cents internally and returned as decimal JSON numbers. This avoids floating-point rounding errors in balances and budgets.

## MongoDB Atlas setup

Before running the backend, make sure the Atlas project has:

1. A database user with read/write access to the cluster.
2. Your development IP address added to Atlas Network Access.
3. The password URL-encoded if it contains characters such as `@`, `:`, `/`, or `#`.

The test suite uses in-memory fake repositories, so it does not connect to Atlas or change cloud data. The running application uses `MONGODB_URI` and initializes the `transactions` and `budgets` indexes on startup. Local Flutter web origins are allowed through `CORS_ORIGIN_REGEX`.

