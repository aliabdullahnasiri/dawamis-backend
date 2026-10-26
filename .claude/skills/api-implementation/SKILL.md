---
name: api-implementation
description: 'Guide for creating API endpoints in the Dawamis backend. Ensures correct routing, request validation via schemas, dependency injection using Annotated aliases, and strict separation between the API layer and business logic services.'
license: MIT
allowed-tools: Bash
---

# API Implementation Skill

This skill guides the creation of API endpoints in the Dawamis backend. The API layer is responsible for routing, request validation (via schemas), dependency injection, and coordinating service calls.

## API Architecture

The API follows a strict flow:
`HTTP request → router/route validation → dependency injection → service → ORM/Redis/worker → response schema`

### Directory Structure
`src/app/api/`
  - `dependencies/`: Global FastAPI dependencies (DB, Redis, Auth).
  - `middleware/`: Request/Response interceptors.
  - `routers/`: Domain-specific route definitions.
    - `[domain]/`: Domain-specific routers.

## Implementation Rules

### 1. Router Configuration
- Use `APIRouter` with explicit `prefix` and `tags` for OpenAPI documentation.
- Group related endpoints in separate files within `src/app/api/routers/[domain]/`.

### 2. Endpoint Definition
- **Response Models**: Always specify `response_model` in the decorator to ensure the output is shaped by a schema.
- **Status Codes**: Use `status.HTTP_...` for non-200 responses (e.g., `status_code=status.HTTP_201_CREATED` for POST).
- **Docstrings**: Every endpoint must have a concise docstring explaining its purpose.

### 3. Dependency Injection
Use the pre-defined `Annotated` aliases from `src/app/api/dependencies/auth.py` and `src/app/api/dependencies/db.py` instead of repeating `Depends(...)`.

**Common Aliases**:
- `DBSession`: Database session.
- `RedisClient`: Redis client.
- `CurrentUser`: The authenticated `User` object.
- `CurrentActiveSession`: The current authenticated `UserSession`.
- `CurrentClaims`: JWT claims.
- `PermissionRequired["perm_name"]`: For RBAC checks.

### 4. Request & Response Handling
- **Requests**: Use `...Request` schemas for payload validation.
- **Responses**: 
  - Never return ORM models directly.
  - Use `...Data.model_validate(orm_object)` to map ORM entities to data schemas.
  - Wrap the data schema in the corresponding `...Response` envelope.

### 5. Coordination with Services
- **Keep logic thin**: Routers should only handle HTTP concerns (params, status codes, response wrapping).
- **Delegate business rules**: Call the appropriate `[Domain]Service` for all logic, persistence, and security checks.

## Example Endpoint Implementation

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

## Checklist for New Endpoints
- [ ] `response_model` is specified.
- [ ] Correct `Annotated` dependencies are used.
- [ ] Request payload is validated by a `...Request` schema.
- [ ] Business logic is delegated to a service.
- [ ] ORM models are mapped to `...Data` schemas before returning.
- [ ] Docstring is provided.
- [ ] Status code is correct for the operation (e.g., 204 for deletes).
