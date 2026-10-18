from uuid import UUID

from fastapi import Request, status

from app.api.dependencies.auth import CurrentActiveSession, CurrentRefreshToken
from app.api.dependencies.db import DBSession
from app.api.dependencies.redis import RedisClient
from app.api.router import Router
from app.core.config import settings
from app.core.exceptions import AuthenticationError, RateLimitError
from app.core.i18n.types import T
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
)
from app.schemas.auth.data import LoginData, RefreshData
from app.schemas.auth.response import (
    LogoutResponse,
    RefreshResponse,
    RevokeSessionResponse,
    SessionsResponse,
)
from app.schemas.user.data import UserData
from app.services.auth import AuthService, JWTService
from app.services.auth.rate_limit import AuthRateLimiter
from app.services.auth.security import SecurityService
from app.services.auth.session import SessionService
from app.services.auth.two_factor_challenge import TwoFactorChallengeService
from app.services.user import UserService

router = Router(tags=["Authentication - Sessions"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: RegisterRequest,
    db: DBSession,
) -> RegisterResponse:
    """
    Register a new user account.
    """
    user = await AuthService.register(
        db=db,
        data=data,
    )

    await AuthService.send_welcome_email(user)

    return RegisterResponse(
        message=T("auth:registration_successful"),
        data=UserData.model_validate(user),
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
)
async def login(
    data: LoginRequest,
    db: DBSession,
    request: Request,
    redis: RedisClient,
) -> LoginResponse:
    """
    Authenticate a user and generate access and refresh tokens.
    """
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # 1. IP Rate Limit Check
    try:
        if ip_address:
            await AuthRateLimiter.check_ip(redis, ip_address)
    except RateLimitError as e:
        await SecurityService.rate_limit_exceeded(
            db, ip_address=ip_address, user_agent=user_agent
        )
        raise e
    except Exception as e:
        raise e

    # 2. Authentication Attempt
    try:
        user = await AuthService.authenticate(
            db=db,
            email=data.email,
            password=data.password,
        )
    except AuthenticationError:
        # 3. Failure Path
        if ip_address:
            await AuthRateLimiter.record_ip_failure(redis, ip_address)

        # Record user failure if account exists
        try:
            user_to_limit = await UserService.get_by_email(db, email=data.email)
            if user_to_limit:
                attempts = await AuthRateLimiter.record_user_failure(
                    redis, user_to_limit.uuid
                )
                if attempts >= settings.AUTH_RATE_LIMIT_USER:
                    await SecurityService.account_locked(
                        db,
                        user_id=user_to_limit.id,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        attempts=attempts,
                    )
        except Exception:
            pass

        await SecurityService.login_failed(
            db,
            user_id=None,  # User not authenticated
            ip_address=ip_address,
            user_agent=user_agent,
        )
        raise

    # 4. Success Path
    await AuthRateLimiter.reset_user(redis, user.uuid)
    await SecurityService.login_success(
        db, user_id=user.id, ip_address=ip_address, user_agent=user_agent
    )

    if user.totp_enabled:
        challenge_token = await TwoFactorChallengeService.create(
            redis=redis,
            user_id=str(user.uuid),
        )
        return LoginResponse(
            message=T("auth:two_factor_challenge_created"),
            data=LoginData(
                requires_2fa=True,
                challenge_token=challenge_token,
                expires_in=TwoFactorChallengeService.TTL_SECONDS,
            ),
        )

    await SessionService.get_or_create_session(
        db=db,
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    login_data = LoginData(
        access_token=JWTService.create_access_token(
            identity=str(user.uuid),
        ),
        refresh_token=JWTService.create_refresh_token(
            identity=str(user.uuid),
        ),
    )

    return LoginResponse(
        message=T("auth:authentication_successful"),
        data=login_data,
    )


@router.get(
    "/me",
    response_model=UserData,
)
async def me(
    session: CurrentActiveSession,
    db: DBSession,
) -> UserData:
    """
    Return the currently authenticated user.
    """
    return UserData.model_validate(session.user)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
)
async def logout(
    db: DBSession,
    session: CurrentActiveSession,
) -> LogoutResponse:
    """
    Revoke the current access token.
    """
    await SessionService.revoke_session(
        db=db, user_id=session.user_id, session_uuid=session.uuid
    )

    return LogoutResponse(
        message=T("auth:logout_successful"),
    )


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    status_code=status.HTTP_200_OK,
)
async def refresh(
    db: DBSession,
    token: CurrentRefreshToken,
    session: CurrentActiveSession,
) -> RefreshResponse:
    """
    Create a new access token using a valid refresh token.
    """

    claims = JWTService.decode(token)

    if claims.get("type") != "refresh":
        raise AuthenticationError(
            T("auth:invalid_refresh_token"),
        )

    user_id = claims.get("sub")

    if not user_id:
        raise AuthenticationError(
            T("auth:invalid_token"),
        )

    access_token = JWTService.create_access_token(
        identity=user_id,
    )

    return RefreshResponse(
        message=T("auth:access_token_refreshed"),
        data=RefreshData(
            access_token=access_token,
        ),
    )


@router.get(
    "/sessions",
    response_model=SessionsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_sessions(
    db: DBSession,
    session: CurrentActiveSession,
) -> SessionsResponse:
    """
    List all active sessions for the currently authenticated user.
    """
    sessions = await SessionService.get_user_sessions(
        db=db,
        user_id=session.user.id,
    )

    return SessionsResponse(
        message=T("auth:sessions_listed_successfully"),
        data=sessions,
    )


@router.delete(
    "/sessions/{session_uuid}",
    response_model=RevokeSessionResponse,
    status_code=status.HTTP_200_OK,
)
async def revoke_session(
    db: DBSession,
    session: CurrentActiveSession,
    session_uuid: UUID,
) -> RevokeSessionResponse:
    """
    Revoke a specific session for the currently authenticated user.
    """
    await SessionService.revoke_session(
        db=db,
        user_id=session.user.id,
        session_uuid=session_uuid,
    )

    return RevokeSessionResponse(
        message=T("auth:session_revoked_successfully"),
    )


@router.post(
    "/sessions/revoke-all",
    response_model=RevokeSessionResponse,
    status_code=status.HTTP_200_OK,
)
async def revoke_all_sessions(
    db: DBSession,
    session: CurrentActiveSession,
) -> RevokeSessionResponse:
    """
    Revoke all sessions for the currently authenticated user.
    """
    await SessionService.revoke_all_sessions(
        db=db,
        user_id=session.user.id,
    )

    return RevokeSessionResponse(
        message=T("auth:all_sessions_revoked_successfully"),
    )
