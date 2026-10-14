# Lumen Finance API

This is the backend foundation for the Flutter expense tracker. It provides a FastAPI HTTP API, SQLite persistence for local development, input validation, owner-scoped records, and calculated monthly summaries.

The code intentionally separates the business service from the persistence adapter. SQLite is a useful first step while the product and API contract are being validated; the service can later use a PostgreSQL repository without changing the Flutter contract or calculation logic.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m app
```

The API is available at `http://127.0.0.1:8000`. Interactive documentation is at `/docs`.

Run checks with:

```powershell
pytest
```

## API surface

- `GET /health`
- `GET /api/v1/transactions`
- `POST /api/v1/transactions`
- `GET /api/v1/transactions/{id}`
- `PATCH /api/v1/transactions/{id}`
- `DELETE /api/v1/transactions/{id}`
- `GET /api/v1/budgets`
- `POST /api/v1/budgets`
- `PATCH /api/v1/budgets/{id}`
- `DELETE /api/v1/budgets/{id}`
- `GET /api/v1/summary?month=YYYY-MM`

Until authentication is added, records are scoped by the `X-User-Id` header. In development it defaults to `demo-user`; set `REQUIRE_USER_HEADER=true` before exposing the service anywhere shared. This header is only a development boundary, not an authentication system.

Amounts are stored as integer cents internally and returned as decimal JSON numbers. This avoids floating-point rounding errors in balances and budgets.

## AWS and database direction

AWS is reasonable once the product needs hosted access, backups, and multi-device sync. The recommended production shape is:

1. FastAPI deployed on ECS/Fargate or a small container platform.
2. PostgreSQL on Amazon RDS or Aurora for users, transactions, budgets, and audit records.
3. Amazon S3 only for receipt images, CSV exports, or other files—not as the primary transaction database.
4. Secrets Manager for database credentials and Cognito or another verified identity provider for authentication.

The current code keeps these decisions reversible. The next database step should be a PostgreSQL adapter plus migrations, followed by authentication and a Flutter API client. Do not move production money data to S3 or ship the `X-User-Id` development header as real security.

