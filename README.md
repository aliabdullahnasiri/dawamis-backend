# DawaMIS Backend

The asynchronous REST API for DawaMIS, a pharmacy management system. This repository currently provides the account, security, and organization foundation: authentication, user profiles, device sessions, email verification, password recovery, two-factor authentication, organization membership, and organization-scoped permissions.

Medicine catalogs, inventory, purchases, sales, invoicing, and supplier workflows are not implemented in the current API.

## Contents

- [Technology](#technology)
- [Local setup](#local-setup)
- [Configuration](#configuration)
- [API reference](#api-reference)
- [Authentication and organization context](#authentication-and-organization-context)
- [Database migrations](#database-migrations)
- [Background tasks and email](#background-tasks-and-email)
- [Development and testing](#development-and-testing)
- [Localization](#localization)
- [Repository structure](#repository-structure)
- [Deployment notes](#deployment-notes)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## Technology

| Area | Implementation |
| --- | --- |
| Runtime | Python 3.14 or newer |
| HTTP API | FastAPI, Uvicorn |
| Validation and settings | Pydantic, pydantic-settings |
| Database | SQLAlchemy 2 async ORM, Alembic, MySQL through asyncmy |
| Test database | SQLite through aiosqlite |
| Cache and transient authentication state | Redis |
| Background tasks | Celery with Redis broker and result backend |
| Authentication | JWT, bcrypt, OTP/TOTP, hashed recovery codes |
| Secret encryption | cryptography Fernet |
| Email | SMTP with Jinja2 templates |
| Localization | Babel/gettext |
| Development | uv, pytest, Ruff, Pyright |

Dependency declarations and locked versions live in [pyproject.toml](pyproject.toml) and [uv.lock](uv.lock).

## Local setup

### 1. Prerequisites

Install Python 3.14+, `uv`, MySQL, and Redis. An SMTP server is needed to receive registration, verification, password-reset, and email OTP messages. A local SMTP capture server can be used during development.

Run commands from the repository root so `.env`, migration configuration, and translation resources resolve correctly.

### 2. Install dependencies

```bash
git clone https://github.com/aliabdullahnasiri/dawamis-backend.git
cd dawamis-backend
uv sync --all-groups
cp .env.example .env
```

The development dependencies include `aiosqlite`, which is required when using SQLite.

### 3. Configure services and secrets

Create a MySQL database and an application user with access to it, then edit `.env`:

```dotenv
DATABASE_URL=mysql+asyncmy://USERNAME:PASSWORD@localhost:3306/DATABASE_NAME
REDIS_URL=redis://localhost:6379/0
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_USE_TLS=false
MAIL_FROM_EMAIL=no-reply@example.com
MAIL_FROM_NAME=Dawamis
FRONTEND_URL=http://localhost:3000
```

Percent-encode special characters in database URL credentials. Ensure MySQL, Redis, and your SMTP server are running at the configured addresses.

Generate separate application and JWT secrets, and a Fernet encryption key:

```bash
uv run python -c "import secrets; print(secrets.token_urlsafe(48))"
uv run python -c "import secrets; print(secrets.token_urlsafe(48))"
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the outputs into `SECRET_KEY`, `JWT_SECRET_KEY`, and `TOTP_ENCRYPTION_KEY`, respectively. The encryption key must be a valid Fernet key: the placeholder in `.env.example` cannot be used to start the application or collect tests. Keep this key stable; replacing it makes existing encrypted two-factor secrets unreadable.

### 4. Apply migrations

```bash
uv run alembic upgrade head
```

Startup registers the permission definitions idempotently. It does not create the schema or default roles; organization owners create and assign roles through the RBAC endpoints.

### 5. Start the API

```bash
uv run uvicorn app:main --factory --reload --host 127.0.0.1 --port 8000
```

`app:main` is an application factory. The `app` project script returns the FastAPI instance; use Uvicorn to serve it.

| Resource | Local URL |
| --- | --- |
| Swagger UI | http://127.0.0.1:8000/docs |
| ReDoc | http://127.0.0.1:8000/redoc |
| OpenAPI schema | http://127.0.0.1:8000/openapi.json |
| API prefix | http://127.0.0.1:8000/api/v1 |

### 6. Start background processes

In separate terminals, using the same environment configuration:

```bash
uv run celery -A app.core.celery:celery_app worker --include app.workers --loglevel=info
```

```bash
uv run celery -A app.workers.meta:celery_app beat --loglevel=info
```

The worker's explicit include loads the task classes. The Beat entrypoint imports the workers package so its schedules are registered; Beat does not accept the worker's `--include` option. Both commands use the same Celery application. The worker processes queued email; Beat schedules periodic session cleanup.

## Configuration

Settings are defined in [src/app/core/settings.py](src/app/core/settings.py). Environment variables override `.env`, names are case-sensitive, and unknown settings are ignored. Restart API and worker processes after changing configuration.

### Application and services

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_NAME` | `DawaMIS API` | API title and Celery application name |
| `APP_DESCRIPTION` | Backend API description | OpenAPI description |
| `APP_VERSION` | `1.0.0` | OpenAPI application version |
| `APP_ENV` | `development` | Environment setting |
| `APP_DEBUG` | `true` | Debug setting; not currently passed to FastAPI |
| `TIMEZONE` | `Asia/Kabul` | Celery timezone |
| `DATABASE_URL` | `sqlite+aiosqlite:///dev.db` | Async database connection URL |
| `REDIS_URL` | `redis://localhost:6379/0` | Authentication state, Celery broker, and result backend |
| `SECRET_KEY` | Development placeholder | Session-cookie signing key; replace before use |
| `FRONTEND_URL` | `http://localhost:3000` | Base URL for frontend links in emails |

The template uses MySQL while the settings fallback uses SQLite. MySQL is the documented migration setup; SQLite-backed model tests do not establish migration compatibility. `EDITION` appears in `.env.example` but is not a declared setting and currently has no effect.

### Email

| Variable | Default |
| --- | --- |
| `SMTP_HOST` | `smtp.example.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USERNAME` | `username@example.com` |
| `SMTP_PASSWORD` | Development placeholder |
| `SMTP_USE_TLS` | `true` |
| `MAIL_FROM_EMAIL` | `noreply@dawamis.com` |
| `MAIL_FROM_NAME` | `Dawamis` |

`SMTP_USE_TLS=true` enables STARTTLS. SMTP authentication occurs when both username and password are nonempty. The current delivery implementation uses SMTP, not the Mailtrap API, although its SDK is a dependency.

### Authentication and two-factor settings

| Variable | Default | Purpose |
| --- | --- | --- |
| `JWT_SECRET_KEY` | `dev-jwt-secret` | JWT signing secret; replace before use |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access-token lifetime |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Refresh-token lifetime |
| `AUTH_RATE_LIMIT_IP` | `10` | Failed authentication threshold per IP |
| `AUTH_RATE_LIMIT_IP_WINDOW` | `300` | IP rate-limit window, seconds |
| `AUTH_RATE_LIMIT_USER` | `5` | Failed authentication threshold per user |
| `AUTH_RATE_LIMIT_USER_WINDOW` | `900` | User rate-limit window, seconds |
| `TOTP_ENCRYPTION_KEY` | Invalid placeholder | Fernet key for encrypted two-factor secrets |
| `RECOVERY_CODE_COUNT` | `10` | Number of generated recovery codes |
| `TOTP_VALID_WINDOW` | `1` | Accepted TOTP window tolerance; template sets `2` |

Additional settings include `DEFAULT_ROLES`, `SUPPORTED_LANGUAGES`, `DEFAULT_LANGUAGE`, and `LOCALES_DIR`. See the settings class for their types and defaults.

## API reference

All paths below are relative to `/api/v1`. The generated OpenAPI schema describes request bodies, response models, and dependencies in detail.

### Accounts and sessions

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/auth/register` | Register an account |
| POST | `/auth/login` | Authenticate or begin a two-factor challenge |
| GET | `/auth/me` | Return the authenticated user |
| POST | `/auth/logout` | Revoke the current session |
| POST | `/auth/refresh` | Issue an access token using a refresh token |
| GET | `/auth/sessions` | List active sessions |
| DELETE | `/auth/sessions/{session_uuid}` | Revoke one session |
| POST | `/auth/sessions/revoke-all` | Revoke all user sessions |
| POST | `/auth/password/forgot` | Request password-reset email |
| POST | `/auth/password/reset` | Reset a password with a token |
| POST | `/auth/password/change` | Change the current user's password |
| POST | `/auth/email/verify` | Verify an email token |
| POST | `/auth/email/resend` | Request another verification email |

### Two-factor authentication

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/auth/2fa/totp/setup` | Prepare authenticator-app enrollment |
| POST | `/auth/2fa/totp/enable` | Confirm TOTP and return recovery codes |
| POST | `/auth/2fa/totp/disable` | Disable TOTP |
| POST | `/auth/2fa/totp/recovery-codes` | Regenerate recovery codes |
| POST | `/auth/2fa/otp/setup` | Prepare email OTP enrollment |
| POST | `/auth/2fa/otp/resend` | Send another email OTP |
| POST | `/auth/2fa/otp/enable` | Confirm email OTP and return recovery codes |
| POST | `/auth/2fa/otp/disable` | Disable email OTP |
| POST | `/auth/2fa/verify` | Complete a login challenge |

### Profiles, organizations, and health

| Method | Path | Purpose |
| --- | --- | --- |
| GET, PATCH, DELETE | `/users/me` | Read, update, or delete the current account |
| PATCH | `/users/me/email` | Change email address |
| PATCH | `/users/me/username` | Change username |
| POST, GET | `/organizations` | Create or list accessible organizations |
| GET, PATCH, DELETE | `/organizations/{organization_uuid}` | Read, update, or delete an organization |
| POST | `/organizations/{organization_uuid}/join-requests` | Email the owner a request to join |
| GET, POST | `/organizations/{organization_uuid}/members` | List or add members |
| PATCH, DELETE | `/organizations/{organization_uuid}/members/{member_uuid}` | Update or remove membership |
| POST | `/auth/organizations/{organization_uuid}/select` | Select the session's organization |
| GET | `/auth/organization` | Read the selected organization |
| GET | `/health/` | Check the database using an authenticated session |

Organization and member lists accept `offset` and `limit`; the default limit is 50 and the maximum is 100. Access and mutation rules are enforced by the organization service. Branches have no standalone CRUD router. Organization roles and permissions use the endpoints below.

Organization resource endpoints enforce access through `PermissionRequired`: reading an organization requires `organizations.read`, listing its members requires `organizations.members.read`, updates/deletions require `organizations.update`/`organizations.delete`, and membership changes require `organizations.members.manage`. Organization owners pass these permission checks automatically after membership validation.

### Organization RBAC

Resource path identifiers are UUIDs, consistent with the organization API. These paths are relative to `/api/v1/organizations/{organization_uuid}`:

| Method | Path | Required permission |
| --- | --- | --- |
| GET | `/roles` | `roles:read` |
| POST | `/roles` | `roles:create` |
| GET | `/roles/{role_uuid}` | `roles:read` |
| PATCH | `/roles/{role_uuid}` | `roles:update` |
| DELETE | `/roles/{role_uuid}` | `roles:delete` |
| GET | `/permissions` | `permissions:read` |
| GET | `/roles/{role_uuid}/permissions` | `roles:read` |
| PUT | `/roles/{role_uuid}/permissions` | `roles:permissions:update` |
| GET | `/members/{member_uuid}/roles` | `roles:read` |
| PUT | `/members/{member_uuid}/roles` | `roles:assign` |

Owners pass the permission checks after active membership validation. Other members need the listed permission in the URL's organization. Role names are unique within each organization; role lists support `offset` and `limit` (default 50, maximum 100). System roles are readable and assignable but cannot be edited or deleted.

Create a role with `{"name": "Pharmacist", "description": "Dispenses medicine"}`. PATCH accepts `name` and `description`; a null description clears it. A new role has no grants. Replace its permissions with `{"permissions": ["medicine:read", "medicine:create"]}` and assign it to a membership with `{"role_uuids": ["ROLE_UUID"]}`. Both PUT operations replace the complete set, deduplicate entries, and accept an empty list to revoke the set. Assignment requires an active membership in the same organization. Delegates can only grant or assign permissions they already hold; owners can grant any registered definition.

`GET /permissions` lists the shared definition catalog, not a user's effective grants. Definitions include medicine, supplier, purchase, invoice, and customer permissions from [permissions.py](src/app/core/permissions.py), plus existing organization and RBAC management permissions. Defining a permission never grants it, and unregistered names are rejected with 422. Pharmacy workflow endpoints remain future work.

Effective grants are cached in Redis per organization, user, and database revision, with a `PERMISSION_CACHE_TTL_SECONDS` default of 300. Role, permission, assignment, and member-removal changes advance that revision in the same transaction; old cache entries cannot authorize subsequent requests. Membership, organization status, sessions, and ownership are checked separately on every request. Redis failures fall back to database queries. Code that directly changes grant tables must also call `PermissionService.invalidate` in its transaction.

The RBAC migration copies each legacy shared role and its permissions into each organization that used it, preserving existing assignments. Original roles remain as legacy templates without tenant access. Downgrade preserves independent grants and renames duplicate role names to restore global uniqueness.

### Response conventions

Most successful endpoints use an envelope:

```json
{
  "success": true,
  "message": "Localized message",
  "data": {}
}
```

Optional `null` envelope fields may be omitted. `/auth/me` returns user data directly, `/health/` returns a status object, and successful 204 deletions have no body.

Domain errors use their HTTP status and a body containing `type` and `message`. Missing ORM rows are translated to 404. Request/schema validation errors currently return **HTTP 433**, with an `errors` array, rather than FastAPI's default 422 response. Clients should inspect both the HTTP status and response body.

## Authentication and organization context

### Register and log in

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"developer@example.com","user_name":"developer","password":"example-password123","accept_terms":true}'

curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"developer@example.com","password":"example-password123"}'
```

Login accepts JSON. For accounts without two-factor authentication, tokens are returned under `data.access_token` and `data.refresh_token`. Supply the access token as a bearer token:

```bash
curl http://127.0.0.1:8000/api/v1/users/me \
  -H 'Authorization: Bearer ACCESS_TOKEN'

curl -X POST http://127.0.0.1:8000/api/v1/auth/refresh \
  -H 'Authorization: Bearer REFRESH_TOKEN'
```

The refresh token belongs in the Authorization header, not a JSON body. Refresh returns a new access token. The current session lookup uses request client/device information, including IP and User-Agent; keep these consistent when testing login, authenticated requests, and refresh.

Swagger's OAuth password-form flow does not match the JSON login endpoint, and the declared OAuth token URLs omit the API prefix. Obtain tokens through a JSON request when using the interactive documentation.

### Two-factor login

When two-factor authentication is enabled, login returns `requires_2fa`, a `challenge_token`, and `expires_in` instead of normal tokens. Complete `/auth/2fa/verify` using the challenge bearer token and a body containing `code`. The selected provider verifies the code; recovery codes are also supported. A successfully consumed challenge cannot be reused. Enrollment and recovery-code endpoints require the dependencies described in OpenAPI.

### Organization selection and permissions

An authenticated user can request access with `POST /api/v1/organizations/{organization_uuid}/join-requests` (no body). The endpoint returns 202 after queuing an email to the owner containing the requester's username, email, and user ID. It does not create membership or select the organization. The owner reviews the request and uses the existing member-management endpoint to add the user, or reactivate an existing inactive membership. Active members, inactive organizations, and organizations without an owner cannot receive a new join request through this endpoint.

Organizations are selected per session:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/organizations/ORGANIZATION_UUID/select \
  -H 'Authorization: Bearer ACCESS_TOKEN'

curl http://127.0.0.1:8000/api/v1/auth/organization \
  -H 'Authorization: Bearer ACCESS_TOKEN'
```

The current organization dependency rechecks membership and organization activity. `PermissionRequired["permission", ...]` checks the organization identified by `organization_uuid` in the URL, or the session's selected organization when the URL has none. It requires an active session and active membership. The organization's owner passes permission checks automatically; other members need every requested permission through roles in that organization. Owners can manage inactive organizations; selected-organization context still requires an active organization. Grants are not merged across organizations, and there is no implicit superuser bypass.

## Database migrations

Alembic reads `DATABASE_URL` from application settings and uses the ORM metadata.

```bash
# Inspect state
uv run alembic current
uv run alembic heads
uv run alembic history

# Apply pending migrations
uv run alembic upgrade head

# After changing models, generate and review a candidate migration
uv run alembic revision --autogenerate -m "describe schema change"
uv run alembic check
```

Review generated operations, constraints, data handling, and upgrade/downgrade behavior before applying a migration. Validate against the intended database engine. Use backups and a reviewed rollback plan for deployed databases; do not rewrite revisions already applied to shared environments.

## Background tasks and email

`EmailSendWorker` queues plain-text or Jinja-rendered messages under the `email.send` task. `MailService` delivers them using SMTP. A successful API request that queues mail does not establish delivery; check worker logs and the SMTP server.

`SessionCleanupWorker` registers the `session.cleanup` task, scheduled every 15 minutes. Run one Beat scheduler per deployment to avoid duplicate periodic dispatch.

Workers inherit a base implementation that runs async work through a worker event loop and supports automatic retries with backoff. API, worker, and scheduler processes must share compatible database, Redis, encryption, timezone, and mail configuration. Email templates are under `src/app/templates/emails/`.

## Development and testing

```bash
# Entire suite
uv run pytest

# Focused areas
uv run pytest tests/api/auth
uv run pytest tests/services/organization/test_service.py

# Coverage
uv run pytest --cov=app --cov-report=term-missing

# Static checks
uv run ruff check .
uv run pyright
```

Tests cover API routes, models, schemas, services, organization access, JWT, sessions, passwords, and OTP/TOTP. Shared fixtures use an in-memory SQLite database, transaction rollback, HTTPX ASGI transport, email-task mocks, and fake Redis where requested. Application imports still require valid settings, including the Fernet key.

The test suite creates ORM tables directly; it does not replace migration testing on MySQL. The HTTP client fixture does not explicitly execute application lifespan. The HTTP client fixture supplies fake Redis for permission checks. Email mocks remain opt-in; check dependency overrides when adding integration tests.

Pytest uses strict asyncio mode and session-scoped default event loops and async fixtures. Reuse the established fixtures and restore dependency overrides after tests.

## Localization

Configured language mappings are English (`en` → `en_US`), Persian (`fa` → `fa_IR`), and Pashto (`ps` → `ps_AF`). The repository currently contains an English catalog; Persian and Pashto catalogs must be added for translated messages in those languages.

Locale resolution checks `?lang=`, then the stored session language, then `Accept-Language`, then the default. Responses include `Content-Language`.

```bash
# Extract and update existing catalogs
uv run pybabel extract -F babel.cfg -o locales/messages.pot .
uv run pybabel update -i locales/messages.pot -d locales

# Compile edited catalogs
uv run pybabel compile -d locales
```

To start a new catalog, use `uv run pybabel init -i locales/messages.pot -d locales -l fa_IR` (or `ps_AF`), translate its entries, and compile. Runtime translation helpers live under `src/app/core/i18n/`.

## Repository structure

```text
src/app/
├── __init__.py       # FastAPI factory, lifespan, exception handlers
├── api/              # Routers, dependencies, middleware, async validation
├── core/             # Settings, security, encryption, errors, i18n, Celery
├── enums/            # Domain and security enums
├── extensions/       # Database sessions, Redis, console
├── models/           # ORM models and associations
├── schemas/          # Request, response, data, and internal contracts
├── services/         # Business logic and infrastructure services
├── templates/        # Email templates
└── workers/          # Celery tasks and registration
alembic/              # Migration environment and revision history
locales/              # gettext catalogs
tests/                # API, model, schema, and service tests
.env.example          # Local configuration template
pyproject.toml        # Dependencies, project metadata, pytest settings
uv.lock               # Locked dependency resolution
```

Requests pass through middleware, router validation and dependency injection, services, and persistence or background dispatch. Response schemas define the public contract. [CLAUDE.md](CLAUDE.md) contains additional contributor and architecture guidance; source and tests are authoritative where guidance differs.

## Deployment notes

Use a process manager or container runtime to run the API, Celery worker, and Beat separately. A basic API command is:

```bash
uv run uvicorn app:main --factory --host 0.0.0.0 --port 8000
```

Terminate HTTPS at your deployment ingress, provide secrets through the deployment environment, apply reviewed migrations before serving traffic, and retain the translation catalogs and email templates with the application. Restrict database and Redis access to the required services.

The current CORS middleware explicitly allows `http://localhost:3000`. `FRONTEND_URL` controls email links and does **not** configure CORS; update the middleware deliberately for your frontend origin. Setting `APP_ENV` or `APP_DEBUG` does not automatically configure production behavior.

The authenticated `/api/v1/health/` endpoint checks the database, not Redis, SMTP, or worker availability. Configure service monitoring accordingly. `Dockerfile` and `Makefile` are currently empty; this repository does not yet supply a working container build or Make targets.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Fernet key error during import or test collection | Replace `TOTP_ENCRYPTION_KEY` with a generated Fernet key and restart processes |
| Database connection failure | Confirm the async URL, encoded credentials, database/user grants, and server availability |
| Missing tables or columns | Apply migrations to the same database configured for the running process |
| Redis connection error during login or task dispatch | Confirm `REDIS_URL` and Redis availability |
| Email never arrives | Confirm worker registration, pending tasks, SMTP credentials/TLS, and capture-server or delivery logs |
| Unregistered Celery task | Start the worker with `--include app.workers` |
| Periodic cleanup does not run | Use the documented Beat entrypoint so schedules are registered, and confirm a worker is running |
| Browser CORS rejection | Match the browser origin to the explicit middleware allowlist |
| Health check returns an authentication error | Supply an access token with an active matching session |
| Authenticated request fails after login | Check token type, expiry/revocation, and consistent client IP/User-Agent |
| Organization context is rejected | Select an organization and check its activity and the user's current membership |
| Validation error has an unexpected status | The current validation handler intentionally returns HTTP 433 |

## Contributing

Keep HTTP handling in routers, business rules in services, persistence in models, and public contracts in schemas. Follow the existing async dependency and centralized exception patterns. Include migrations for schema changes and focused tests for behavior changes, especially authorization, expiry, revocation, and replay cases.

Before opening a change, run the relevant tests and static checks, inspect the diff, and keep credentials and `.env` out of Git. Document configuration or API changes alongside their implementation.

No license file is currently included in this repository.
