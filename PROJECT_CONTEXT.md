# Project Context: Dawamis Backend

This document serves as a comprehensive system prompt and context guide for LLMs to act as experts on the Dawamis Backend project.

## 🚀 Project Overview
Dawamis is a Python-based backend application built with FastAPI, using an asynchronous architecture to handle user authentication, session management, and background tasks.

## 🛠 Tech Stack
- **Language**: Python 3.12+
- **Framework**: FastAPI
- **Database**: SQLAlchemy (Async) with PostgreSQL
- **Migrations**: Alembic (via `uv run alembic`)
- **Task Queue**: Celery (for background workers)
- **Package Manager**: `uv`
- **Validation**: Pydantic v2
- **Security**: JWT for authentication, bcrypt for password hashing

## 🏗 Core Architecture
The project follows a layered architecture to ensure separation of concerns:

1. **API Layer (`src/app/api`)**:
   - **Routers**: Define endpoints and handle HTTP requests/responses.
   - **Dependencies**: Handle authentication (e.g., `CurrentActiveSession`) and database sessions.
2. **Service Layer (`src/app/services`)**:
   - Contains the core business logic.
   - Services are typically stateless and called by routers.
   - Example: `AuthService`, `SessionService`, `UserService`.
3. **Model Layer (`src/app/models`)**:
   - SQLAlchemy async models defining the database schema.
   - Base class located in `src/app/models/base.py`.
4. **Worker Layer (`src/app/workers`)**:
   - Celery tasks for long-running or asynchronous operations (e.g., `EmailSendWorker`, `SessionCleanupWorker`).
   - Uses a `BaseWorker` ABC for consistency.
5. **Schema Layer (`src/app/schemas`)**:
   - Pydantic models for request validation and response serialization.
   - Divided into `request`, `response`, and `data` categories.

## 🎨 Coding Standards & Idioms
- **Async Everywhere**: All database and I/O operations use `async`/`await`.
- **Type Hinting**: Strict use of Python type hints. Use `TypeAlias` for complex types (e.g., `JSONValue` in `src/app/types/__init__.py`).
- **Error Handling**: Centralized error handling using a custom `AppError` class and FastAPI exception handlers (`src/app/errors`).
- **Naming Conventions**:
  - Classes: `PascalCase`
  - Functions/Variables: `snake_case`
  - Services: Suffix with `Service` (e.g., `AuthService`).
  - Workers: Suffix with `Worker` (e.g., `EmailSendWorker`).
- **Dependency Injection**: Leverages FastAPI's `Depends()` for database sessions and authenticated user context.

## 🗄 Domain Models
- **User**: Core identity entity. Stores credentials, profile info, and account status (e.g., `failed_login_attempts`, `locked_until`).
- **UserSession**: Tracks active logins, IP addresses, user agents, and expiration timestamps.

## ⚙️ Infrastructure & Tooling
- **Database Migrations**:
  - Run via `uv run alembic`.
  - Workflow: `alembic check` $\rightarrow$ `alembic revision --autogenerate` $\rightarrow$ Review $\rightarrow$ `alembic upgrade head`.
- **Background Tasks**:
  - Managed by Celery.
  - Task registration is handled via a metaclass `WorkerMeta` in `src/app/workers/meta.py`.
  - Periodic tasks are defined in the worker's `beat_schedule`.

## 📡 API Patterns
- **Request Pattern**: `...Request` schema $\rightarrow$ Router $\rightarrow$ Service $\rightarrow$ DB.
- **Response Pattern**: `...Response` schema (usually wrapping a `...Data` model) $\rightarrow$ Router.
- **Authentication**: Uses Bearer tokens. The `CurrentActiveSession` dependency is the primary way to access the authenticated user and their current session.

## 🛠 Key Files for Reference
- `src/app/__init__.py`: Application entry point and FastAPI setup.
- `src/app/core/security.py`: JWT and password logic.
- `src/app/api/routers/auth.py`: Main authentication endpoints.
- `src/app/services/session.py`: Session lifecycle management.
- `.gitignore`: Project exclusion rules.
