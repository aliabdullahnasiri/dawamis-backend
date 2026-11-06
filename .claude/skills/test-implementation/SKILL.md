---
name: test-implementation
description: 'Create or update Dawamis backend pytest tests for API endpoints, services, schemas, and models using the existing async, database, authentication, mail, and Redis fixtures. Use when implementing regression coverage or changing tests in this repository.'
---

# Test Implementation Skill

Build tests around observable behavior using this repository's existing fixtures. Before writing, read `tests/conftest.py`, the pytest settings in `pyproject.toml`, the implementation under test, and a nearby test. Verify current signatures and response contracts instead of copying stale examples.

## Placement and reference tests

Paths below are relative to the repository root.

| Layer | Location | Useful reference |
| --- | --- | --- |
| API | `tests/api/`, with domain subdirectories | `tests/api/test_users.py`, `tests/api/auth/test_sessions.py` |
| Services | `tests/services/[domain]/test_*.py` | `tests/services/organization/test_service.py` |
| Schemas | `tests/schemas/[domain]/test_requests.py`, `test_responses.py`, `test_data.py` | `tests/schemas/user/test_requests.py` |
| Models | `tests/models/test_<entity>.py` | `tests/models/test_branch.py` |
| Redis-backed security | Under the relevant API or service domain | `tests/services/auth/two_factor/test_two_factor_challenge.py` |

Use `test_<behavior>` functions with focused assertions. Keep ordinary schema validation and pure helper tests synchronous. Mark async tests with `@pytest.mark.asyncio` and declare async fixtures with `@pytest_asyncio.fixture`: pytest runs in strict asyncio mode. Both default test and fixture event-loop scopes are currently `session`; preserve compatibility when adding fixtures.

## Shared fixtures and isolation

- `db_engine`: session-scoped in-memory SQLite engine using `StaticPool`. Autouse `create_tables` creates ORM metadata once; this does not test Alembic migrations or production database compatibility.
- `db_session`: per-test `AsyncSession` bound to a connection transaction, with teardown rollbacks. It also calls `set_db(session)` for context-based schema validators. Reuse it for persistence tests, including services that commit internally; do not replace it with the application's production session factory.
- `client`: HTTPX `AsyncClient` with `ASGITransport`, base URL `http://test`, and a generated User-Agent. It overrides `get_db` and removes that override at teardown. Use `/api/v1/...` paths. This fixture does not explicitly run app lifespan; tests requiring startup behavior need deliberate setup.
- `mock_mail`: patches `EmailSendWorker.send` and `send_template`, exposing mocks under `['send']` and `['send_template']`. Request it whenever a path may enqueue mail; it is not autouse.
- `mock_redis`: returns `fakeredis.FakeAsyncRedis(decode_responses=True)` and patches `app.extensions.redis`. It is not autouse. Pass it directly to services accepting Redis. Verify the consumer's import/dependency path for API tests: already-bound imports may require a targeted patch or dependency override.
- `test_user`: registers a user through the API and returns the response's `data` dictionary, not an ORM `User`.
- `fake_session`: registers and logs in a user, sets the client's Authorization header using `setdefault`, and returns client headers, not a database session.
- `fake_login`: logs in `test_user`, replaces the client's Authorization header, and returns login response data.

Choose one suitable authentication helper rather than composing fixtures that register conflicting users. Clear or explicitly replace Authorization when checking anonymous or alternate-user behavior. Local dependency overrides must be restored after the test.

## Assertions by layer

### API tests

- Exercise routing, validation, authentication, response shaping, and relevant persistence through `client`.
- Assert the status before reading payload fields, preferably `assert response.status_code == expected, response.text`.
- Inspect the established `response.json()['data']` envelope where applicable. For 204 responses, verify an empty body rather than decoding JSON.
- Test malformed requests with raw dictionaries so local Pydantic construction does not intercept errors intended for the API.
- Cover relevant unauthenticated, wrong-user, missing-resource, duplicate, and invalid-input paths using the current error contract. Do not infer working permission enforcement merely from RBAC model names.
- For updates/deletes, verify persisted state or a subsequent request when that proves the behavior more clearly than the immediate response alone.

### Service and model tests

- Use actual `db_session` persistence for queries, constraints, relationships, and state transitions. These are database-backed tests even when located under services.
- Populate required model fields and related entities. Use real password hashing helpers when authentication is exercised; a dummy hash only fits tests that never validate a password.
- Call the service with its actual signature. Cover successful behavior and applicable domain exceptions with `pytest.raises(SpecificError)`; avoid broad exception tuples that conceal unrelated failures.
- Query or refresh persisted objects when checking stored changes, deletion, or cascades. After an expected database integrity failure, roll back before further operations on that session.
- Do not assume SQLite proves production database constraints or migration correctness; validate those separately when the change depends on them.

### Schema tests

- Construct valid models and check relevant fields, serialization, response envelopes, and omission behavior.
- Use `pytest.raises(ValidationError)` for invalid synchronous field constraints, testing required fields and meaningful boundaries.
- For database-backed async validators, request `db_session`, construct the schema, and explicitly `await model.model_async_validate()`. Construction alone does not execute the async validation hook. Assert the exception actually defined by the validator.
- For PATCH contracts, distinguish omitted fields, explicit `None`, and false/empty values where supported; inspect `model_fields_set` or `model_dump(exclude_unset=True)` when relevant.

## External effects and security cases

Mock external delivery and worker dispatch while keeping the behavior being tested real. Patch the name used by the consumer; use `AsyncMock` for awaited functions and ordinary mocks for synchronous enqueue methods. Assert important dispatch arguments without sending email or contacting real Redis.

For authentication changes, select relevant cases such as expired/revoked tokens, token-purpose mismatch, wrong-user challenges, recovery-code consumption, or reuse rejection. The challenge tests demonstrate deleting a fake Redis key to simulate missing/expired state and consuming a challenge twice to test replay protection. This verifies missing-state handling, not Redis TTL timing. Prefer controlled clocks or explicit expired state over sleeps for time boundaries.

## Verification workflow

Run the changed test file first, then related coverage when the change affects shared behavior. Use the full suite for broad changes to fixtures, authentication, or persistence. Run applicable lint/type checks for Python edits; report failures without weakening assertions to make them pass.

```bash
rtk uv run pytest tests/services/organization/test_service.py
rtk uv run pytest tests/api/auth tests/services/auth
rtk uv run pytest
rtk uv run ruff check tests/path/to/changed_test.py
rtk uv run pyright
```

Replace example paths with the actual scope. Report exactly what ran and whether it passed; distinguish test failures from collection or environment failures. Documentation-only changes need skill validation, not an application test run.
