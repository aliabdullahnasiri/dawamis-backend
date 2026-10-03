from enum import StrEnum


class SecurityEventType(StrEnum):
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    SUSPICIOUS_LOGIN = "suspicious_login"
    ACCOUNT_LOCKED = "account_locked"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

    PASSWORD_CHANGED = "password_changed"
    PASSWORD_RESET = "password_reset"

    SESSION_CREATED = "session_created"
    SESSION_REVOKED = "session_revoked"
    ALL_SESSIONS_REVOKED = "all_sessions_revoked"
