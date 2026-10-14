from app.api.dependencies.auth import CurrentActiveSession
from app.api.dependencies.db import DBSession
from app.api.router import Router
from app.core.exceptions import AuthenticationError
from app.core.i18n.types import T
from app.schemas.auth.data import RecoveryCodesData, TwoFactorSetupData
from app.schemas.auth.request import (
    TwoFactorDisableRequest,
    TwoFactorEnableRequest,
    TwoFactorVerifyRequest,
)
from app.schemas.auth.response import RecoveryCodesResponse, TwoFactorSetupResponse
from app.schemas.base.response import BaseResponseModel
from app.services.auth.two_factor import TwoFactorService

router = Router(prefix="/2fa", tags=["Authentication - Two Factor"])


@router.post(
    "/setup",
    response_model=TwoFactorSetupResponse,
)
async def setup_2fa(
    session: CurrentActiveSession,
    db: DBSession,
) -> TwoFactorSetupResponse:
    """
    Initialize TOTP setup for the current user.
    """
    data = await TwoFactorService.setup(
        db=db,
        user=session.user,
    )

    return TwoFactorSetupResponse(
        message=T("auth:two_factor_setup_started"),
        data=TwoFactorSetupData(**data),
    )


@router.post(
    "/enable",
    response_model=RecoveryCodesResponse,
)
async def enable_2fa(
    data: TwoFactorEnableRequest,
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
    response_model=BaseResponseModel[None],
)
async def verify_2fa(
    data: TwoFactorVerifyRequest,
    session: CurrentActiveSession,
    db: DBSession,
) -> BaseResponseModel[None]:
    """
    Verify a TOTP or recovery code.
    """
    # 1. Try TOTP verification
    if await TwoFactorService.verify_totp(session.user, data.code):
        return BaseResponseModel(
            message=T("auth:two_factor_verified_successfully"),
        )

    # 2. Try recovery code verification
    if await TwoFactorService.verify_recovery_code(
        db=db,
        user=session.user,
        code=data.code,
    ):
        return BaseResponseModel(
            message=T("auth:recovery_code_verified_successfully"),
        )

    raise AuthenticationError(T("auth:invalid_two_factor_code"))


@router.post(
    "/recovery-codes",
    response_model=RecoveryCodesResponse,
)
async def regenerate_recovery_codes(
    data: TwoFactorVerifyRequest,
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
