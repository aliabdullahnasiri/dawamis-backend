from app.core.exceptions.base import AppError
from app.core.i18n.types import T


class AuthenticationError(AppError):
    """Raised when authentication fails."""

    code = 401
    type = "authentication_error"
    message = T("auth:authentication_failed")


class TokenError(AuthenticationError):
    """Raised when a JWT is invalid or unusable."""

    type = "token_error"
    message = T("auth:invalid_token")


class TokenIdentityError(TokenError):
    """Raised when a JWT is missing identity (sub claim)."""

    type = "token_identity_error"
    message = T("auth:invalid_token_identity")


class RefreshTokenError(TokenError):
    """Raised when a refresh token is invalid."""

    type = "refresh_token_error"
    message = T("auth:invalid_refresh_token")


class TokenRevokedError(TokenError):
    """Raised when a revoked JWT is used."""

    type = "token_revoked"
    message = T("auth:token_revoked")


class PasswordResetTokenExpiredError(AuthenticationError):
    """Raised when a password reset token has expired."""

    type = "password_reset_token_expired"
    message = T("errors:password_reset_token_expired")


class EmailVerificationTokenExpiredError(AuthenticationError):
    """Raised when an email verification token has expired."""

    code = 400
    type = "email_verification_token_expired"
    message = T("errors:email_verification_token_expired")


class SessionNotFoundError(AppError):
    """Raised when an authentication session cannot be found."""

    code = 404
    type = "session_not_found"
    message = T("auth:session_not_found")


class InvalidPasswordResetTokenError(AppError):
    """Raised when a password reset token is invalid."""

    code: int = 400
    type: str = "invalid_password_reset_token"
    message: str = T("errors:invalid_password_reset_token")


class TwoFactorError(AuthenticationError):
    """Base exception for Two-Factor authentication errors."""

    type = "two_factor_error"


class InvalidTwoFactorChallengeError(AuthenticationError):
    """Raised when the 2FA challenge token is invalid."""

    type = "invalid_two_factor_challenge"
    message = T("auth:invalid_two_factor_challenge")


class TwoFactorChallengeExpiredError(AuthenticationError):
    """Raised when the 2FA challenge token has expired."""

    type = "two_factor_challenge_expired"
    message = T("auth:two_factor_challenge_expired")


class TwoFactorAlreadyEnabledError(TwoFactorError):
    """Raised when 2FA is already enabled for the user."""

    code = 400
    type = "two_factor_already_enabled"
    message = T("auth:two_factor_already_enabled")


class TwoFactorSetupRequiredError(TwoFactorError):
    """Raised when 2FA setup is required before enabling."""

    code = 400
    type = "two_factor_setup_required"
    message = T("auth:two_factor_setup_required")


class InvalidTwoFactorCodeError(TwoFactorError):
    """Raised when the provided TOTP code is invalid."""

    code = 401
    type = "invalid_two_factor_code"
    message = T("auth:invalid_two_factor_code")


class TwoFactorNotEnabledError(TwoFactorError):
    """Raised when 2FA operations are attempted but not enabled."""

    code = 400
    type = "two_factor_not_enabled"
    message = T("auth:two_factor_not_enabled")


class InvalidTwoFactorPasswordError(TwoFactorError):
    """Raised when the password provided during 2FA disable is incorrect."""

    code = 401
    type = "invalid_two_factor_password"
    message = T("auth:invalid_password")
