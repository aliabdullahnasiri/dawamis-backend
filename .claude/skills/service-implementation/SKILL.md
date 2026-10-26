---
name: service-implementation
description: 'Guide for creating business logic services in the Dawamis backend. Enforces async-first I/O, standard transaction patterns, domain-driven error handling with localization, and comprehensive unit test coverage.'
license: MIT
allowed-tools: Bash
---

# Service Implementation Skill

This skill guides the creation of business logic services in the Dawamis backend. Services are the primary layer for reusable business rules, coordinating persistence, security, and background work.

## Service Architecture

Services must follow the layered design: `HTTP request → router/route validation → dependency injection → service → ORM/Redis/worker → response schema`.

### Implementation Rules

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
   - Use the `@handle_exception(OriginalError, _raise=DomainError)` decorator for simple mapping of SQLAlchemy errors (like `NoResultFound`) to domain errors.
   - Use localized messages via `T("namespace:key")` for all user-facing errors.

5. **Validation & Constraints**:
   - Perform uniqueness checks (e.g., for emails or slugs) before creation or updates.
   - Validate entity existence before performing dependent operations (e.g., check if an Organization exists before adding a Branch).

6. **Type Hinting**:
   - Use modern Python type hints.
   - Use actual model types (e.g., `-> User`) and schema types for request data (e.g., `data: CreateUserRequest`).
   - Use `UUID` for UUID fields.

## Standard Method Patterns

### Creation
```python
@staticmethod
async def create(db: AsyncSession, data: CreateRequest) -> Model:
    entity = Model(**data.model_dump())
    db.add(entity)
    await db.commit()
    await db.refresh(entity)
    return entity
```

### Retrieval (Safe)
```python
@staticmethod
async def get_by_uuid(db: AsyncSession, entity_uuid: UUID) -> Model:
    entity = (await db.execute(select(Model).where(Model.uuid == entity_uuid))).scalar_one_or_none()
    if entity is None:
        raise ModelNotFoundError(message=T("domain:not_found"))
    return entity
```

### Update
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

## Testing Workflow

Every new service must be accompanied by unit tests in `tests/services/[domain]/test_service.py`.

1. Use the `db_session` fixture for isolated database access.
2. Cover the "Happy Path" (successful creation/retrieval/update).
3. Cover "Negative Paths" (not found, conflict errors, validation failures).
4. Ensure all constraints (like `NOT NULL` fields) are satisfied in test setup.
