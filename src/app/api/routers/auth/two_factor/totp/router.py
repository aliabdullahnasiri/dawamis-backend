

from app.api.dependencies.auth import (
    CurrentActiveSession,
)
from app.api.dependencies.db import DBSession
from app.api.router import Router
from app.core.i18n.types import T
from app.schemas.auth import (
    RecoveryCodesData,
    RecoveryCodesResponse,
    TOTPEnableRequest,
    TOTPSetupData,
    TOTPSetupResponse,
    TOTPVerifyRequest,
)
from app.schemas.auth.request.two_factor import TwoFactorDisableRequest
from app.schemas.base.response import BaseResponseModel
from app.services.auth.two_factor import TwoFactorService

router = Router(prefix="/totp", tags=["Authentication - Two Factor TOTP"])


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
