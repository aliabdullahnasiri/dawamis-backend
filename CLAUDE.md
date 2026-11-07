# CLAUDE.md — Dawamis Backend

Consolidated project context and implementation guidance from `PROJECT_CONTEXT.md` and `.claude/skills/{api,schema,service,test}-implementation/SKILL.md`. The project context review date below is inherited from the source; consolidation does not imply a new code review.


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

`src/app/api/routes.py` builds the main API router through `create_app_router()`, currently including authentication, health, users, and organizations routers. `AsyncValidationRoute` calls `model_async_validate()` on request arguments that are instances of the project's schema `Model`.

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

`current_user_can(*permissions)` requires an active session, a selected active organization, an active membership, and every named permission through roles scoped to that organization. It does not merge grants across organizations or grant an implicit owner/superuser bypass.

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

Prefer the existing `Annotated` aliases and FastAPI dependencies rather than repeating `Depends(...)` throughout endpoint signatures. Aliases include `DBSession`, `RedisClient`, `OAuth2Token`, `RefreshToken`, `CurrentToken`, `CurrentRefreshToken`, `CurrentClaims`, `CurrentUserUUID`, `CurrentUser`, `CurrentActiveSession`, `CurrentOrganization`, and `Current2FAChallenge`. Confirm the exact import path and current definition before using one.

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

Application errors derive from `AppError` in `src/app/core/exceptions/`. They carry a code, machine-readable type, and message. Central exception handlers are registered during app setup. Uncaught SQLAlchemy `NoResultFound` exceptions are mapped centrally to HTTP 404 with the existing `not_found` error envelope; explicit domain errors retain their messages. Prefer established domain exceptions and add new exceptions within the existing hierarchy where appropriate; avoid broad try/except blocks in every endpoint.

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

## 17. API Implementation Skill

Source: `.claude/skills/api-implementation/SKILL.md`.


This skill guides the creation of API endpoints in the Dawamis backend. The API layer is responsible for routing, request validation (via schemas), dependency injection, and coordinating service calls.

### API Architecture

The API follows a strict flow:
`HTTP request → router/route validation → dependency injection → service → ORM/Redis/worker → response schema`

#### Directory Structure
`src/app/api/`
  - `dependencies/`: Global FastAPI dependencies (DB, Redis, Auth).
  - `middleware/`: Request/Response interceptors.
  - `routers/`: Domain-specific route definitions.
    - `[domain]/`: Domain-specific routers.

### Implementation Rules

#### 1. Router Configuration
- Use `APIRouter` with explicit `prefix` and `tags` for OpenAPI documentation.
- Group related endpoints in separate files within `src/app/api/routers/[domain]/`.

#### 2. Endpoint Definition
- **Response Models**: Always specify `response_model` in the decorator to ensure the output is shaped by a schema.
- **Status Codes**: Use `status.HTTP_...` for non-200 responses (e.g., `status_code=status.HTTP_201_CREATED` for POST).
- **Docstrings**: Every endpoint must have a concise docstring explaining its purpose.

#### 3. Dependency Injection
Use the pre-defined `Annotated` aliases from `src/app/api/dependencies/auth.py` and `src/app/api/dependencies/db.py` instead of repeating `Depends(...)`.

**Common Aliases**:
- `DBSession`: Database session.
- `RedisClient`: Redis client.
- `CurrentUser`: The authenticated `User` object.
- `CurrentActiveSession`: The current authenticated `UserSession`.
- `CurrentClaims`: JWT claims.
- `PermissionRequired["perm_name"]`: For RBAC checks.

#### 4. Request & Response Handling
- **Requests**: Use `...Request` schemas for payload validation.
- **Responses**: 
  - Never return ORM models directly.
  - Use `...Data.model_validate(orm_object)` to map ORM entities to data schemas.
  - Wrap the data schema in the corresponding `...Response` envelope.

#### 5. Coordination with Services
- **Keep logic thin**: Routers should only handle HTTP concerns (params, status codes, response wrapping).
- **Delegate business rules**: Call the appropriate `[Domain]Service` for all logic, persistence, and security checks.

### Example Endpoint Implementation

```python
@router.patch("/me", response_model=GetUserResponse)
async def update_me(
    request: UpdateUserRequest,
    session: CurrentActiveSession,
    db: DBSession,
) -> GetUserResponse:
    """
    Update the profile of the currently authenticated user.
    """
    # 1. Delegate business logic to the service
    updated_user = await UserService.update(db, session.user, request)
    
    # 2. Shape the response using the Data schema and Response envelope
    return GetUserResponse(data=UserData.model_validate(updated_user))
```

### Checklist for New Endpoints
- [ ] `response_model` is specified.
- [ ] Correct `Annotated` dependencies are used.
- [ ] Request payload is validated by a `...Request` schema.
- [ ] Business logic is delegated to a service.
- [ ] ORM models are mapped to `...Data` schemas before returning.
- [ ] Docstring is provided.
- [ ] Status code is correct for the operation (e.g., 204 for deletes).

## 18. Schema Implementation Skill

Source: `.claude/skills/schema-implementation/SKILL.md`.


This skill guides the creation of Pydantic schemas for the Dawamis backend. Schemas define the API contracts, ensuring strict validation of incoming requests and consistent shaping of outgoing responses.

### Schema Architecture

The project uses a strictly categorized schema tree to separate concerns:
`src/app/schemas/`
  - `base/`: Core base models and shared logic.
  - `[domain]/`: Domain-specific schemas.
    - `request/`: Input validation schemas.
    - `response/`: Output shaping schemas.
    - `data/`: Internal data transfer models (not used directly as API boundaries).
    - `internal/`: Private logic/internal processing schemas.

### Implementation Rules

#### 1. Base Model Inheritance
All schemas must inherit from the project's `Model` base class to support asynchronous validation.

- **Requests**: Inherit from `BaseRequestModel` (e.g., `class CreateUserRequest(BaseRequestModel):`).
- **Responses**: Inherit from `BaseResponseModel[T]` (e.g., `class UserResponse(BaseResponseModel[UserData]):`).

#### 2. Naming Conventions
Follow strict suffix naming to clearly identify the purpose of the schema:
- **Request Schemas**: End in `Request` (e.g., `UpdateUserRequest`).
- **Response Schemas**: End in `Response` (e.g., `UserResponse`).
- **Data Models**: End in `Data` or describe the entity (e.g., `UserData`).

#### 3. Validation Rules

##### Field Validation
Use Pydantic `Field` for basic constraints:
- `min_length`, `max_length` for strings.
- `EmailStr` for email validation.
- `default=None` for optional fields in PATCH requests.

##### Asynchronous Validation
For validations requiring database access (e.g., uniqueness checks), use `@async_field_validator`.

- **Pattern**: Use the `Unique` validator from `app.schemas.validators.unique` to avoid duplicating DB logic.
- **Logic**:
  ```python
  @async_field_validator("field_name")
  async def _validate_field(self: Self) -> None:
      await Unique(Model.field, T("namespace:error_key")).validate(self.field_name)
  ```
- **Nuance**: In `Update` requests, ensure the validator is only called if the field is actually provided (check `if self.field_name:`).

#### 4. Response Shaping
- **Exclusion**: Response models use `__exclude_none__ = True` to keep payloads clean.
- **Separation**: Never return ORM models directly in the response. Always map the ORM model to a `...Data` schema, then wrap that in a `...Response` schema.

### Directory Structure Pattern

When adding a new domain (e.g., `organization`), create the following structure:
`src/app/schemas/organization/`
  - `request/`: Put `CreateOrganizationRequest`, `UpdateOrganizationRequest` here.
  - `response/`: Put `OrganizationResponse` here.
  - `data/`: Put `OrganizationData` here.

### Example Implementation

#### Request Schema
```python
class CreateOrganizationRequest(BaseRequestModel):
    name: str = Field(..., min_length=1, max_length=150)
    slug: str = Field(..., min_length=1, max_length=150)

    @async_field_validator("slug")
    async def _validate_slug(self) -> None:
        await Unique(Organization.slug, T("organization:slug_already_exists")).validate(self.slug)
```

#### Response Schema
```python
class OrganizationData(Model):
    id: int
    name: str
    slug: str

class OrganizationResponse(BaseResponseModel[OrganizationData]):
    pass
```

## 19. Service Implementation Skill

Source: `.claude/skills/service-implementation/SKILL.md`.


This skill guides the creation of business logic services in the Dawamis backend. Services are the primary layer for reusable business rules, coordinating persistence, security, and background work.

### Service Architecture

Services must follow the layered design: `HTTP request → router/route validation → dependency injection → service → ORM/Redis/worker → response schema`.

#### Implementation Rules

1. **Class Structure**:
   - Use a class named `[Domain]Service` (e.g., `UserService`, `OrganizationService`).
   - Use `@staticmethod` or `@classmethod` for all methods. Do not create service-object lifecycles (instantiation).
   - Use descriptive docstrings for the class and every method.

2. **Async-First I/O**:
   - Use `async def` and `await` for all database (SQLAlchemy) and Redis calls.
   - Keep pure helper methods synchronous.

3. **Persistence & Transactions**:
   - Pass `AsyncSession` (aliased as `db`) as the first argument to methods requiring database access.
   - Handle commits and refreshes explicitly: `await db.commit()` and `await db.refresh(entity)`.
   - Use `select(...)` and `scalar_one_or_none()` or `scalar_one()` for retrievals.

4. **Error Handling**:
   - Raise established domain exceptions from `app.core.exceptions`.
   - Use localized messages via `T("namespace:key")` for all user-facing errors.

5. **Validation & Constraints**:
   - Perform uniqueness checks (e.g., for emails or slugs) before creation or updates.
   - Validate entity existence before performing dependent operations (e.g., check if an Organization exists before adding a Branch).

6. **Type Hinting**:
   - Use modern Python type hints.
   - Use actual model types (e.g., `-> User`) and schema types for request data (e.g., `data: CreateUserRequest`).
   - Use `UUID` for UUID fields.

### Standard Method Patterns

#### Creation
```python
@staticmethod
async def create(db: AsyncSession, data: CreateRequest) -> Model:
    entity = Model(**data.model_dump())
    db.add(entity)
    await db.commit()
    await db.refresh(entity)
    return entity
```

#### Retrieval (Safe)
```python
@staticmethod
async def get_by_uuid(db: AsyncSession, entity_uuid: UUID) -> Model:
    entity = (await db.execute(select(Model).where(Model.uuid == entity_uuid))).scalar_one_or_none()
    if entity is None:
        raise ModelNotFoundError(message=T("domain:not_found"))
    return entity
```

#### Update
```python
@staticmethod
async def update(db: AsyncSession, entity: Model, **kwargs) -> Model:
    for key, value in kwargs.items():
        if value is not None:
            setattr(entity, key, value)
    await db.commit()
    await db.refresh(entity)
    return entity
```

### Testing Workflow

Every new service must be accompanied by unit tests in `tests/services/[domain]/test_service.py`.

1. Use the `db_session` fixture for isolated database access.
2. Cover the "Happy Path" (successful creation/retrieval/update).
3. Cover "Negative Paths" (not found, conflict errors, validation failures).
4. Ensure all constraints (like `NOT NULL` fields) are satisfied in test setup.

## 20. Test Implementation Skill

Source: `.claude/skills/test-implementation/SKILL.md`.


Build tests around observable behavior using this repository's existing fixtures. Before writing, read `tests/conftest.py`, the pytest settings in `pyproject.toml`, the implementation under test, and a nearby test. Verify current signatures and response contracts instead of copying stale examples.

### Placement and reference tests

Paths below are relative to the repository root.

| Layer | Location | Useful reference |
| --- | --- | --- |
| API | `tests/api/`, with domain subdirectories | `tests/api/test_users.py`, `tests/api/auth/test_sessions.py` |
| Services | `tests/services/[domain]/test_*.py` | `tests/services/organization/test_service.py` |
| Schemas | `tests/schemas/[domain]/test_requests.py`, `test_responses.py`, `test_data.py` | `tests/schemas/user/test_requests.py` |
| Models | `tests/models/test_<entity>.py` | `tests/models/test_branch.py` |
| Redis-backed security | Under the relevant API or service domain | `tests/services/auth/two_factor/test_two_factor_challenge.py` |

Use `test_<behavior>` functions with focused assertions. Keep ordinary schema validation and pure helper tests synchronous. Mark async tests with `@pytest.mark.asyncio` and declare async fixtures with `@pytest_asyncio.fixture`: pytest runs in strict asyncio mode. Both default test and fixture event-loop scopes are currently `session`; preserve compatibility when adding fixtures.

### Shared fixtures and isolation

- `db_engine`: session-scoped in-memory SQLite engine using `StaticPool`. Autouse `create_tables` creates ORM metadata once; this does not test Alembic migrations or production database compatibility.
- `db_session`: per-test `AsyncSession` bound to a connection transaction, with teardown rollbacks. It also calls `set_db(session)` for context-based schema validators. Reuse it for persistence tests, including services that commit internally; do not replace it with the application's production session factory.
- `client`: HTTPX `AsyncClient` with `ASGITransport`, base URL `http://test`, and a generated User-Agent. It overrides `get_db` and removes that override at teardown. Use `/api/v1/...` paths. This fixture does not explicitly run app lifespan; tests requiring startup behavior need deliberate setup.
- Reuse `mock_mail` for email-worker mocking in tests; do not repeat per-test patches of `EmailSendWorker.send` or `send_template`. Assert against `mock_mail["send"]` or `mock_mail["send_template"]`.
- `mock_mail`: patches `EmailSendWorker.send` and `send_template`, exposing mocks under `['send']` and `['send_template']`. Request it whenever a path may enqueue mail; it is not autouse.
- `mock_redis`: returns `fakeredis.FakeAsyncRedis(decode_responses=True)` and patches `app.extensions.redis`. It is not autouse. Pass it directly to services accepting Redis. Verify the consumer's import/dependency path for API tests: already-bound imports may require a targeted patch or dependency override.
- `test_user`: registers a user through the API and returns the response's `data` dictionary, not an ORM `User`.
- `fake_session`: registers and logs in a user, sets the client's Authorization header using `setdefault`, and returns client headers, not a database session.
- `fake_login`: logs in `test_user`, replaces the client's Authorization header, and returns login response data.

Choose one suitable authentication helper rather than composing fixtures that register conflicting users. Clear or explicitly replace Authorization when checking anonymous or alternate-user behavior. Local dependency overrides must be restored after the test.

### Assertions by layer

#### API tests

- Exercise routing, validation, authentication, response shaping, and relevant persistence through `client`.
- Assert the status before reading payload fields, preferably `assert response.status_code == expected, response.text`.
- Inspect the established `response.json()['data']` envelope where applicable. For 204 responses, verify an empty body rather than decoding JSON.
- Test malformed requests with raw dictionaries so local Pydantic construction does not intercept errors intended for the API.
- Cover relevant unauthenticated, wrong-user, missing-resource, duplicate, and invalid-input paths using the current error contract. Do not infer working permission enforcement merely from RBAC model names.
- For updates/deletes, verify persisted state or a subsequent request when that proves the behavior more clearly than the immediate response alone.

#### Service and model tests

- Use actual `db_session` persistence for queries, constraints, relationships, and state transitions. These are database-backed tests even when located under services.
- Populate required model fields and related entities. Use real password hashing helpers when authentication is exercised; a dummy hash only fits tests that never validate a password.
- Call the service with its actual signature. Cover successful behavior and applicable domain exceptions with `pytest.raises(SpecificError)`; avoid broad exception tuples that conceal unrelated failures.
- Query or refresh persisted objects when checking stored changes, deletion, or cascades. After an expected database integrity failure, roll back before further operations on that session.
- Do not assume SQLite proves production database constraints or migration correctness; validate those separately when the change depends on them.

#### Schema tests

- Construct valid models and check relevant fields, serialization, response envelopes, and omission behavior.
- Use `pytest.raises(ValidationError)` for invalid synchronous field constraints, testing required fields and meaningful boundaries.
- For database-backed async validators, request `db_session`, construct the schema, and explicitly `await model.model_async_validate()`. Construction alone does not execute the async validation hook. Assert the exception actually defined by the validator.
- For PATCH contracts, distinguish omitted fields, explicit `None`, and false/empty values where supported; inspect `model_fields_set` or `model_dump(exclude_unset=True)` when relevant.

### External effects and security cases

Mock external delivery and worker dispatch while keeping the behavior being tested real. Patch the name used by the consumer; use `AsyncMock` for awaited functions and ordinary mocks for synchronous enqueue methods. Assert important dispatch arguments without sending email or contacting real Redis.

For authentication changes, select relevant cases such as expired/revoked tokens, token-purpose mismatch, wrong-user challenges, recovery-code consumption, or reuse rejection. The challenge tests demonstrate deleting a fake Redis key to simulate missing/expired state and consuming a challenge twice to test replay protection. This verifies missing-state handling, not Redis TTL timing. Prefer controlled clocks or explicit expired state over sleeps for time boundaries.

### Verification workflow

Run the changed test file first, then related coverage when the change affects shared behavior. Use the full suite for broad changes to fixtures, authentication, or persistence. Run applicable lint/type checks for Python edits; report failures without weakening assertions to make them pass.

```bash
rtk uv run pytest tests/services/organization/test_service.py
rtk uv run pytest tests/api/auth tests/services/auth
rtk uv run pytest
rtk uv run ruff check tests/path/to/changed_test.py
rtk uv run pyright
```

Replace example paths with the actual scope. Report exactly what ran and whether it passed; distinguish test failures from collection or environment failures. Documentation-only changes need skill validation, not an application test run.
