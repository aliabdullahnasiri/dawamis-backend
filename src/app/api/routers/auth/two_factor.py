from uuid import UUID

from fastapi import Request

from app.api.dependencies.auth import (
    Current2FAChallenge,
    CurrentActiveSession,
    CurrentUser,
)
from app.api.dependencies.db import DBSession
from app.api.dependencies.redis import RedisClient
from app.api.router import Router
from app.core.exceptions import AuthenticationError
from app.core.i18n.types import T
from app.schemas.auth import (
    LoginData,
    RecoveryCodesData,
    RecoveryCodesResponse,
    TOTPEnableRequest,
    TOTPSetupData,
    TOTPSetupResponse,
    TOTPVerifyRequest,
    TwoFactorDisableRequest,
    TwoFactorVerifyResponse,
)
from app.schemas.base.response import BaseResponseModel
from app.services.auth.jwt import JWTService
from app.services.auth.session import SessionService
from app.services.auth.two_factor import TwoFactorService
from app.services.auth.two_factor_challenge import TwoFactorChallengeService
from app.services.user import UserService

router = Router(prefix="/2fa", tags=["Authentication - Two Factor"])


@router.post(
    "/setup",
    response_model=TOTPSetupResponse,
)
async def setup_2fa(
    session: CurrentActiveSession,
    db: DBSession,
) -> TOTPSetupResponse:
    """
    Initialize TOTP setup for the current user.
    """
    data = await TwoFactorService.setup(
        db=db,
        user=session.user,
    )

    return TOTPSetupResponse(
        message=T("auth:two_factor_setup_started"),
        data=TOTPSetupData(**data),
    )


@router.post(
    "/enable",
    response_model=RecoveryCodesResponse,
)
async def enable_2fa(
    data: TOTPEnableRequest,
    session: CurrentActiveSession,
    db: DBSession,
) -> RecoveryCodesResponse:
    """
    Verify the first TOTP code and enable 2FA.
    """
    codes = await TwoFactorService.enable(
        db=db,
        user=session.user,
        code=data.code,
    )

    return RecoveryCodesResponse(
        message=T("auth:two_factor_enabled_successfully"),
        data=RecoveryCodesData(recovery_codes=codes),
    )


@router.post(
    "/disable",
    response_model=BaseResponseModel[None],
)
async def disable_2fa(
    data: TwoFactorDisableRequest,
    session: CurrentActiveSession,
    db: DBSession,
) -> BaseResponseModel[None]:
    """
    Disable two-factor authentication.
    """
    await TwoFactorService.disable(
        db=db,
        user=session.user,
        password=data.password,
        code=data.code,
    )

    return BaseResponseModel(
        message=T("auth:two_factor_disabled_successfully"),
    )


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
    if await TwoFactorService.verify_totp(user, data.code):
        verified = True
    elif await TwoFactorService.verify_recovery_code(db, user, data.code):
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


@router.post(
    "/recovery-codes",
    response_model=RecoveryCodesResponse,
)
async def regenerate_recovery_codes(
    data: TOTPVerifyRequest,
    session: CurrentActiveSession,
    db: DBSession,
) -> RecoveryCodesResponse:
    """
    Regenerate recovery codes after verifying a TOTP code.
    """
    codes = await TwoFactorService.regenerate_recovery_codes(
        db=db,
        user=session.user,
        code=data.code,
    )

    return RecoveryCodesResponse(
        message=T("auth:recovery_codes_regenerated_successfully"),
        data=RecoveryCodesData(recovery_codes=codes),
    )
