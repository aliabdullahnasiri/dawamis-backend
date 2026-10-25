# PROJECT_CONTEXT.md — Dawamis Backend

This document is a working guide for developers and AI assistants contributing to this repository. Read it before editing code. The source code, tests, migrations, and current environment are authoritative if anything here conflicts with them.

- Repository: https://github.com/aliabdullahnasiri/dawamis-backend
- Default branch: `main`
- Reviewed: 2026-10-25

## 1. Project purpose and current scope

Dawamis (DawaMIS) is the backend API for a pharmacy-management system. The current repository focuses on the API foundation, users, authentication, sessions, email verification, password reset, two-factor authentication, security events, organization/branch/role/permission models, localization, and background workers.

Do not assume all pharmacy workflows (medicines, stock, purchases, invoices, suppliers, and similar modules) are implemented here just because they belong to the wider product vision. Inspect actual routes, services, models, and tests before extending a feature.

## 2. Technology stack

- **Python:** `>=3.14`, according to `pyproject.toml` and `.python-version`.
- **API:** FastAPI and Uvicorn.
- **Validation/settings:** Pydantic v2 and `pydantic-settings`.
- **Persistence:** SQLAlchemy 2 async ORM and Alembic.
- **Drivers:** `asyncmy` for MySQL; `aiosqlite` for development/testing. `.env.example` uses MySQL, while `settings.py` defaults to SQLite. Do not assume PostgreSQL is the active database.
- **Transient state:** asynchronous Redis client.
- **Background work:** Celery.
- **Security:** PyJWT, bcrypt, `cryptography`, `pyotp`, QR-code generation, email OTP, hashed recovery codes.
- **Email:** Jinja2 templates and Mailtrap integration.
- **Localization:** Babel/gettext catalogs in `locales/`.
- **Tooling:** `uv`, pytest, pytest-asyncio, pytest-cov, Ruff, Pyright, HTTPX, fakeredis.
- Clerk backend SDK is listed as a dependency; inspect its actual use before making assumptions about its role.

Use `pyproject.toml` and `uv.lock` for the current dependency versions.

## 3. Repository map

```text
src/app/
  __init__.py                 FastAPI app setup, lifespan, exception registration
  run.py                      Application runner
  api/
    router.py                 Custom Router and route class
    routes.py                 Main API router assembly and async schema validation
    dependencies/             DB, Redis, OAuth, authentication dependencies
    middleware/               Database-related and locale middleware
    routers/
      auth/                   Authentication, sessions, passwords, verification, 2FA
      health.py               Health endpoint
      users.py                User/profile endpoints
  core/
    config.py                 Settings export
    settings.py               Pydantic Settings and defaults
    celery.py                 Celery app setup
    startup.py                Startup initialization
    encryption.py             Secret encryption helpers
    decorators.py             Shared decorators
    context/                  Request/database context helpers
    exceptions/               AppError hierarchy and exception handlers
    i18n/                     Translation and locale context
    security/manager.py       Token, user and session security orchestration
    worker_database.py        Worker database/event-loop support
  enums/                      Domain/security enums
  extensions/db.py            Async engine and session factory
  extensions/redis.py         Shared async Redis client
  models/                      SQLAlchemy models and association tables
  schemas/                     Request, response, data, internal schemas
  services/                    Auth, user, JWT, sessions, 2FA, mail and utilities
  templates/emails/            Jinja email templates
  workers/                      Celery worker base, registration, email and session tasks
locales/                        Translation catalogs
alembic/                        Migration environment and revisions
tests/                          API, model, schema, service and 2FA tests
.claude/skills/                 Repository-specific Claude skills
.env.example                    Environment variable template
pyproject.toml                  Dependencies and tool configuration
pyrightconfig.json              Pyright configuration
```

## 4. Architecture and request flow

Typical flow:

`HTTP request → router/route validation → dependency injection → service → ORM/Redis/worker → response schema`

- **Routers** define paths, request dependencies, status codes, and response schemas. Keep business logic out of route functions when it belongs in a service.
- **Services** contain reusable business rules and coordinate persistence, security, and background work. Existing services commonly use `@staticmethod` and `@classmethod`.
- **Models** define SQLAlchemy tables, relationships, constraints, and model-level behavior.
- **Schemas** validate requests and shape responses. The schema tree separates request, response, data, and internal models.
- **Dependencies** provide DB sessions, Redis, token values, authenticated users, active sessions, and 2FA challenges.
- **Workers** execute asynchronous task implementations through Celery's synchronous entry point.
- **Core** contains configuration, errors, localization, security, startup, encryption, and worker support.

### Application setup

`src/app/__init__.py` defines an `App` class that creates FastAPI, installs lifespan handling, registers the API under `/api/v1`, registers exception handlers, and installs middleware. The class uses a singleton-style `__new__`. Startup opens a database session and runs `Startup`; shutdown is currently a placeholder.

`src/app/api/routes.py` builds the main API router through `create_app_router()`, currently including authentication, health, and users routers. `AsyncValidationRoute` calls `model_async_validate()` on request arguments that are instances of the project's schema `Model`.

### Database and Redis

- `src/app/extensions/db.py` creates the async SQLAlchemy engine and `SessionLocal`.
- Current engine settings: `pool_size=20`, `max_overflow=0`, `pool_pre_ping=True`.
- Session settings: `autoflush=False`, `autocommit=False`, `expire_on_commit=False`.
- `get_db()` yields a session from an async context manager.
- `src/app/extensions/redis.py` creates a shared `redis.asyncio.Redis` client using `settings.REDIS_URL` and `decode_responses=True`.
- Understand transaction ownership before adding commits or rollbacks. Some service methods commit internally.
- Await async DB and Redis calls. Avoid synchronous database operations in async request paths.

## 5. Models and domain concepts

The model package includes:

- `User`: profile, email verification, password-reset state, failed-login/lockout fields, 2FA state, roles, organization memberships, sessions, recovery codes, security events.
- `UserSession`: user, IP address, user agent, last-used time, expiry and revocation timestamps.
- `Role` and `Permission`, with role-permission and user-role association tables.
- `Organization` and `Branch`, plus organization-user association.
- `SecurityEvent`: security/audit records.
- `RecoveryCode`: one-time recovery-code records.
- `RevokedToken`: token revocation records.

Do not assume all models are fully integrated into endpoint authorization. In particular, inspect the implementation and tests before relying on RBAC: the current `current_user_can` dependency contains a placeholder, so permission enforcement must not be assumed complete just because permission models exist.

### Base model

`src/app/models/base.py` defines `DeclarativeBaseMeta` and shared SQLAlchemy `Base`. It provides an integer primary key, UUID, UTC `created_at`/`updated_at` timestamps, `to_dict()`, `to_json()`, and `__hidden_fields__`. Keep password hashes, tokens, private secrets, and authentication data out of API responses and logs. When changing models, check relationships, constraints, serialization, tests, and Alembic history.

## 6. Authentication and security

Main locations: `src/app/api/routers/auth/`, `src/app/services/auth/`, `src/app/core/security/`, and `src/app/api/dependencies/auth.py`.

- **Password hashing:** the `User` model uses bcrypt helpers.
- **JWT:** `JWTService` creates and decodes tokens. Access and refresh tokens have different claims/types; refresh validation checks token type and revocation.
- **Sessions:** `SessionService` and `UserSession` support active-session lookup, expiry, revocation, and session-management endpoints. `CurrentActiveSession` is a central dependency pattern.
- **Email verification/password reset:** dedicated services and routers manage token hashes and expiry. Templates live under `src/app/templates/emails/auth/`.
- **Rate limiting:** `AuthRateLimiter` uses Redis and configurable IP/user thresholds. Example defaults are 10 attempts per IP per 300 seconds and 5 attempts per user per 900 seconds. Use settings, not hard-coded values.
- **Security manager:** `SecurityManager` validates tokens, resolves user identity, and finds active sessions. Preserve its exception semantics; do not weaken validation.
- **Two-factor authentication:** both email OTP and authenticator-app TOTP providers exist. `TwoFactorService` selects the provider from the configured user method. TOTP uses `pyotp` and QR provisioning. Email OTP derives a six-digit code from a stored secret over a five-minute time window and sends it by email. Recovery codes are stored as hashes and consumed when used. Do not describe 2FA as email-only or TOTP-only; check the selected method and endpoint.
- **Encryption:** `SecretEncryption` protects 2FA secrets. Encryption keys belong in environment configuration, never in Git.
- **Challenges:** a separate 2FA challenge token/service exists. Do not treat challenge tokens as ordinary access tokens; enforce purpose and expiry.
- **Audit events:** reuse the existing security event model/enums when recording security-relevant actions.

Security changes should consider replay, expiry, brute-force attempts, session revocation, transaction consistency, information leakage, and negative-path tests.

## 7. Dependency injection

Prefer the existing `Annotated` aliases and FastAPI dependencies rather than repeating `Depends(...)` throughout endpoint signatures. Aliases include `DBSession`, `RedisClient`, `OAuth2Token`, `RefreshToken`, `CurrentToken`, `CurrentRefreshToken`, `CurrentClaims`, `CurrentUserUUID`, `CurrentUser`, `CurrentActiveSession`, and `Current2FAChallenge`. Confirm the exact import path and current definition before using one.

A valid access token, an existing user, an active session, and a 2FA challenge are distinct things. Choose the dependency matching the endpoint's security requirements.

## 8. Schemas and API contracts

- Request schemas usually end in `Request`; response schemas in `Response`; payload models commonly end in `Data`.
- Base schema types are under `src/app/schemas/base/`.
- Feature schemas are grouped by request/response/data/internal purpose.
- Use Pydantic constraints for validation and preserve the async validation hook where custom validation is required.
- Follow `BaseResponseModel` and nearby endpoint response patterns. Do not invent a new response envelope without need.
- Avoid returning ORM objects directly when a response schema exists.
- Keep client-facing errors localizable and avoid exposing internal exception details.

## 9. Errors and localization

Application errors derive from `AppError` in `src/app/core/exceptions/`. They carry a code, machine-readable type, and message. Central exception handlers are registered during app setup. Prefer established domain exceptions and add new exceptions within the existing hierarchy where appropriate; avoid broad try/except blocks in every endpoint.

Localization lives in `src/app/core/i18n/` and `locales/`. Current language mapping: `en → en_US`, `fa → fa_IR`, `ps → ps_AF`; default language is English. Middleware handles locale context. Code uses translation keys through `T("namespace:key")`. Follow existing key conventions and update catalogs for new user-facing messages.

## 10. Workers and email

- `BaseWorker` is the abstract Celery worker base. Its synchronous `run()` delegates to asynchronous `_run()` through the event loop managed by `worker_database.py`.
- `WorkerMeta` automatically registers concrete worker classes with Celery and applies class-defined beat schedules.
- `EmailSendWorker` delegates to `MailService` and supports plain and template-based email. Its methods enqueue tasks using `.delay()`; email is not necessarily sent inline.
- `SessionCleanupWorker` handles session cleanup; inspect its current schedule before changing it.
- Worker defaults include retrying exceptions with backoff and up to five retries.
- Templates use Jinja2 under `src/app/templates/emails/`.

Follow existing base class, naming, registration, async execution, and scheduling patterns when adding workers. Consider task argument serialization and failure/retry behavior.

## 11. Migrations

Migration files live in `alembic/versions/`; configuration is in `alembic.ini` and `alembic/env.py`.

Suggested workflow:

1. Inspect the model change and current migration heads.
2. Run `uv run alembic check` if supported by the configured database.
3. Generate a candidate migration: `uv run alembic revision --autogenerate -m "describe change"`.
4. Review and edit the generated migration; autogenerate is not a substitute for review.
5. Check upgrade/downgrade logic, nullability, indexes, foreign keys, data migrations, and DB compatibility.
6. Apply locally with `uv run alembic upgrade head` and run relevant tests.

Do not casually edit an applied migration. The history includes user sessions, security events, password reset, and multiple stages of 2FA changes. Inspect the revision chain before changing these areas.

## 12. Tests and developer tools

Tests are grouped under `tests/api`, `tests/models`, `tests/schemas`, and `tests/services`. Coverage includes health/users, authentication, passwords, sessions, verification, OTP/TOTP, JWT, schemas, and domain models.

- Run focused tests first, then the broader suite.
- Full suite: `uv run pytest`
- Focused test: `uv run pytest tests/api/auth/test_sessions.py`
- Ruff: `uv run ruff check .`
- Pyright: `uv run pyright`
- Migration state: `uv run alembic heads` and `uv run alembic check`
- Pytest uses strict asyncio mode and session-scoped default test/event-loop fixtures as configured in `pyproject.toml`. Keep async fixtures and event loops compatible.
- Reuse fixtures in `tests/conftest.py` and existing SQLite/fake-Redis patterns where appropriate.
- Never claim tests passed unless they were actually run.

## 13. Coding style — follow the author's approach

When implementing features, match this repository's patterns instead of introducing a different architecture for personal preference.

1. **Readable, explicit Python.** Use descriptive names, complete type annotations, and focused docstrings.
2. **Async-first I/O.** Use `async def`/`await` for database, Redis, and other async I/O. Keep pure helpers synchronous.
3. **Layered design.** HTTP concerns belong in routers, reusable business logic in services, persistence in models/services, and long-running work in workers.
4. **Dependency injection.** Reuse the project's annotated dependency aliases and factories. Do not pass request or translator objects through every service unless needed.
5. **Service conventions.** Follow nearby `@staticmethod`/`@classmethod` patterns; do not create unnecessary service-object lifecycles.
6. **Type hints.** Use modern Python typing and actual model/schema types. Avoid `Any` unless needed and don't suppress Pyright without a clear reason.
7. **Centralized errors.** Raise established application/domain exceptions and let registered handlers serialize them. Avoid duplicated endpoint-level error handling.
8. **Schema-driven contracts.** Define request/response schemas and update tests when contracts change.
9. **Naming.** Classes use `PascalCase`; functions, variables, and modules use `snake_case`. Follow suffixes such as `Service`, `Worker`, `Request`, `Response`, and `Data`.
10. **Small changes.** Keep patches focused. Avoid unrelated refactors and public API renames.
11. **Security by default.** Never log passwords, raw OTP/recovery codes, JWTs, encryption keys, or secrets.
12. **Useful comments.** Explain non-obvious choices and security reasoning; don't repeat the code in comments.
13. **Tests are part of the change.** Cover normal behavior, invalid input, authorization, expiry/revocation, and failure paths where relevant.
14. **Check for incomplete features.** Search for placeholders, `pass`, ellipses, TODOs, and empty methods before depending on a feature. Startup initialization methods and the permission-check dependency currently include placeholders.

## 14. Environment and common commands

Copy `.env.example` to `.env` and replace placeholders with local values. Never commit `.env` or real credentials. Settings use environment variables and `.env`, are case-sensitive, and ignore extra values.

```bash
# Install dependencies (including dev group)
uv sync --all-groups

# Run the app; confirm the exact entrypoint in src/app/run.py
uv run uvicorn app:main --factory

# Tests
uv run pytest
uv run pytest tests/api/auth/test_sessions.py

# Quality checks
uv run ruff check .
uv run pyright

# Migration checks
uv run alembic heads
uv run alembic check
```

Verify the actual launch command in `src/app/run.py`, `pyproject.toml`, and `alembic.ini` before relying on it. Ensure the configured database and Redis services are available. Do not expose environment values when debugging.

## 15. Workflow for AI assistants

Before editing:

1. Read this file and inspect `git status`/the current diff.
2. Read the relevant router, service, schema, model, dependency, migration, and tests.
3. Search for existing helpers and similar implementations before adding new ones.
4. Verify the current configuration and behavior; this file is a map, not a substitute for source inspection.
5. Consider API compatibility, security, localization, transaction ownership, and migrations.

While editing:

1. Keep changes focused and consistent with current style.
2. Reuse current exceptions, aliases, response models, translation keys, and services.
3. Preserve async behavior and transaction boundaries.
4. Do not invent dependencies, settings, fields, routes, or helpers without checking source.

Before finishing:

1. Add or update tests for changed behavior.
2. Run relevant tests, lint, and type checks; report exactly what ran and what failed.
3. Review the diff for secrets, accidental API changes, missing migrations, and unrelated edits.
4. Summarize changed files, behavior, tests, and follow-up risks.
5. Update this document if it becomes inaccurate.

## 16. Accuracy notes

- The repository README is currently empty; source code, tests, configuration, and migrations are the primary documentation.
- The tracked `Dockerfile` and `Makefile` are currently empty; do not assume a working container or Make target exists.
- `.env.example` uses MySQL while the settings default uses SQLite. Confirm the active environment before debugging database behavior.
- Both email OTP and authenticator-app TOTP providers exist.
- Some RBAC and startup code is incomplete. Verify behavior rather than inferring completeness from model names or comments.
- This document reflects the repository tree/files reviewed on 2026-10-25. Re-check recent commits before relying on it later.
