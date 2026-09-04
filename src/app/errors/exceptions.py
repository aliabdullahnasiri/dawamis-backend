from app.core.i18n.types import T


class AppError(Exception):
    """
    Base exception for application-level errors.
    """

    status_code: int = 500
    code: str = "internal_error"
    message = T("errors:internal_error")

    def __init__(
        self,
        message: str | None = None,
        *,
        status_code: int | None = None,
        code: str | None = None,
    ) -> None:
        self.message = message if message is not None else self.message

        self.status_code = status_code if status_code is not None else self.status_code

        self.code = code or self.code

        super().__init__(T(self.message))


class BadRequestError(AppError):
    """
    Raised when a request is invalid.
    """

    status_code = 400
    code = "bad_request"
    message = T("request:bad_request")


class AuthenticationError(AppError):
    """
    Raised when authentication fails.
    """

    status_code = 401
    code = "authentication_error"
    message = T("auth:authentication_failed")


class AuthorizationError(AppError):
    """
    Raised when an authenticated user is not authorized
    to perform an action.
    """

    status_code = 403
    code = "authorization_error"
    message = T("auth:permission_denied")


class NotFoundError(AppError):
    """
    Raised when a requested resource does not exist.
    """

    status_code = 404
    code = "not_found"
    message = T("errors:not_found")


class ConflictError(AppError):
    """
    Raised when a request conflicts with the current state
    of a resource.
    """

    status_code = 409
    code = "conflict"
    message = T("errors:conflict")


class ValidationError(AppError):
    """
    Raised when business-level validation fails.
    """

    status_code = 422
    code = "validation_error"
    message = T("validation:failed")


class TokenError(AuthenticationError):
    """
    Raised when a JWT is invalid or unusable.
    """

    code = "token_error"
    message = T("auth:invalid_token")


class TokenRevokedError(TokenError):
    """
    Raised when a revoked JWT is used.
    """

    code = "token_revoked"
    message = T("auth:token_revoked")
