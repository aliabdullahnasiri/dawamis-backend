from app.core.exceptions.base import AppError
from app.core.i18n.types import T


class ValidationError(AppError):
    """Raised when business-level validation fails."""

    code = 422
    type = "validation_error"
    message = T("validation:failed")


class ChallengeTokenRequiredError(ValidationError):
    """Raised when the 2FA challenge token is missing."""

    type = "challenge_token_required"
    message = T("auth:challenge_token_required")


class AuthTokensRequiredError(ValidationError):
    """Raised when access and refresh tokens are missing after login."""

    type = "auth_tokens_required"
    message = T("auth:auth_tokens_required")


class ChallengeTokenForbiddenError(ValidationError):
    """Raised when a challenge token is provided but not expected."""

    type = "challenge_token_forbidden"
    message = T("auth:challenge_token_forbidden")


class InvalidTimestampError(ValidationError):
    """Raised when a provided timestamp is invalid."""

    type = "invalid_timestamp"
    message = T("value_error:invalid_timestamp")


class EmailContentRequiredError(ValidationError):
    """Raised when an email is sent without content."""

    type = "email_content_required"
    message = T("errors:email_must_contain_text_or_html_content")

