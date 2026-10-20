from uuid import UUID

from fastapi import Request

from app.api.dependencies.auth import Current2FAChallenge, CurrentUser
from app.api.dependencies.db import DBSession
from app.api.dependencies.redis import RedisClient
from app.api.router import Router
from app.core.exceptions import AuthenticationError
from app.core.i18n.types import T
from app.schemas.auth import LoginData, TOTPVerifyRequest, TwoFactorVerifyResponse
from app.services.auth.jwt import JWTService
from app.services.auth.session import SessionService
from app.services.auth.two_factor import TwoFactorService
from app.services.auth.two_factor.challenge import TwoFactorChallengeService
from app.services.user import UserService

router = Router(tags=["Authentication - Two Factor Verification"])


@router.post(
    "/verify",
    response_model=TwoFactorVerifyResponse,
)
async def verify_2fa(
    data: TOTPVerifyRequest,
    challenge: Current2FAChallenge,
    db: DBSession,
    user: CurrentUser,
    redis: RedisClient,
    request: Request,
) -> TwoFactorVerifyResponse:
    """
    Verify a TOTP or recovery code and issue session tokens.
    """
    user_id = challenge.user_id
    user = await UserService.get_by_uuid(db, user_uuid=UUID(user_id))

    if not user:
        raise AuthenticationError(T("auth:user_not_found"))

    # 1. Verify TOTP or Recovery Code
    verified = False
    if await TwoFactorService.verify(db, user, data.code) or await TwoFactorService.verify_recovery_code(db, user, data.code):
        verified = True

    if not verified:
        raise AuthenticationError(T("auth:invalid_two_factor_code"))

    # 2. Atomically consume the challenge to prevent replay
    consumed = await TwoFactorChallengeService.consume(
        redis=redis,
        challenge=challenge,
    )

    if not consumed:
        raise AuthenticationError(T("auth:challenge_already_consumed"))

    # 3. Create authenticated session
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    await SessionService.get_or_create_session(
        db=db,
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    # 4. Issue normal tokens
    login_data = LoginData(
        access_token=JWTService.create_access_token(
            identity=str(user.uuid),
        ),
        refresh_token=JWTService.create_refresh_token(
            identity=str(user.uuid),
        ),
    )

    return TwoFactorVerifyResponse(
        message=T("auth:two_factor_verified_successfully"),
        data=login_data,
    )
