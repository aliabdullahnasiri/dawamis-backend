---
name: schema-implementation
description: 'Guide for creating Pydantic schemas in the Dawamis backend. Enforces strict categorization (request, response, data), asynchronous validation patterns for database checks, and consistent naming conventions for API contracts.'
license: MIT
allowed-tools: Bash
---

# Schema Implementation Skill

This skill guides the creation of Pydantic schemas for the Dawamis backend. Schemas define the API contracts, ensuring strict validation of incoming requests and consistent shaping of outgoing responses.

## Schema Architecture

The project uses a strictly categorized schema tree to separate concerns:
`src/app/schemas/`
  - `base/`: Core base models and shared logic.
  - `[domain]/`: Domain-specific schemas.
    - `request/`: Input validation schemas.
    - `response/`: Output shaping schemas.
    - `data/`: Internal data transfer models (not used directly as API boundaries).
    - `internal/`: Private logic/internal processing schemas.

## Implementation Rules

### 1. Base Model Inheritance
All schemas must inherit from the project's `Model` base class to support asynchronous validation.

- **Requests**: Inherit from `BaseRequestModel` (e.g., `class CreateUserRequest(BaseRequestModel):`).
- **Responses**: Inherit from `BaseResponseModel[T]` (e.g., `class UserResponse(BaseResponseModel[UserData]):`).

### 2. Naming Conventions
Follow strict suffix naming to clearly identify the purpose of the schema:
- **Request Schemas**: End in `Request` (e.g., `UpdateUserRequest`).
- **Response Schemas**: End in `Response` (e.g., `UserResponse`).
- **Data Models**: End in `Data` or describe the entity (e.g., `UserData`).

### 3. Validation Rules

#### Field Validation
Use Pydantic `Field` for basic constraints:
- `min_length`, `max_length` for strings.
- `EmailStr` for email validation.
- `default=None` for optional fields in PATCH requests.

#### Asynchronous Validation
For validations requiring database access (e.g., uniqueness checks), use `@async_field_validator`.

- **Pattern**: Use the `Unique` validator from `app.schemas.validators.unique` to avoid duplicating DB logic.
- **Logic**:
  ```python
  @async_field_validator("field_name")
  async def _validate_field(self: Self) -> None:
      await Unique(Model.field, T("namespace:error_key")).validate(self.field_name)
  ```
- **Nuance**: In `Update` requests, ensure the validator is only called if the field is actually provided (check `if self.field_name:`).

### 4. Response Shaping
- **Exclusion**: Response models use `__exclude_none__ = True` to keep payloads clean.
- **Separation**: Never return ORM models directly in the response. Always map the ORM model to a `...Data` schema, then wrap that in a `...Response` schema.

## Directory Structure Pattern

When adding a new domain (e.g., `organization`), create the following structure:
`src/app/schemas/organization/`
  - `request/`: Put `CreateOrganizationRequest`, `UpdateOrganizationRequest` here.
  - `response/`: Put `OrganizationResponse` here.
  - `data/`: Put `OrganizationData` here.

## Example Implementation

### Request Schema
```python
class CreateOrganizationRequest(BaseRequestModel):
    name: str = Field(..., min_length=1, max_length=150)
    slug: str = Field(..., min_length=1, max_length=150)

    @async_field_validator("slug")
    async def _validate_slug(self) -> None:
        await Unique(Organization.slug, T("organization:slug_already_exists")).validate(self.slug)
```

### Response Schema
```python
class OrganizationData(Model):
    id: int
    name: str
    slug: str

class OrganizationResponse(BaseResponseModel[OrganizationData]):
    pass
```
