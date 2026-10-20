from app.api.dependencies.auth import CurrentActiveSession
from app.api.dependencies.db import DBSession
from app.api.router import Router
from app.core.i18n.types import T
from app.schemas.auth.data.two_factor import OTPSetupData, RecoveryCodesData
from app.schemas.auth.request.two_factor import (
    OTPEnableRequest,
    TwoFactorDisableRequest,
)
from app.schemas.auth.response.two_factor import OTPSetupResponse, RecoveryCodesResponse
from app.schemas.base.response import BaseResponseModel
from app.services.auth.two_factor import TwoFactorService
from app.services.auth.two_factor.base import TwoFactorProvider

router = Router(prefix="/otp", tags=["Authentication - Two Factor OTP"])


@router.post(
    "/setup",
    response_model=OTPSetupResponse,
)
async def setup_otp(
    session: CurrentActiveSession,
    db: DBSession,
) -> OTPSetupResponse:
    """
    Initiate OTP setup (sends code via email).
    """
    # Use the TwoFactorService orchestrator to handle setup and persistence
    result = await TwoFactorService.setup(
        db=db,
        user=session.user,
        method="otp",
    )

    return OTPSetupResponse(
        message=T("auth:otp_setup_started"),
        data=OTPSetupData(message=result["message"]),
    )


@router.post(
    "/resend",
    response_model=BaseResponseModel[None],
)
async def resend_otp(
    session: CurrentActiveSession,
    db: DBSession,
) -> BaseResponseModel[None]:
    """
    Resend the OTP verification code for setup.
    """
    # Reuse setup logic to generate and send a new code
    provider: TwoFactorProvider = TwoFactorService._get_provider("otp")
    await provider.setup(db=db, user=session.user)

    return BaseResponseModel(
        message=T("auth:otp_resent_successfully"),
    )


@router.post(
    "/enable",
    response_model=RecoveryCodesResponse,
)
async def enable_otp(
    data: OTPEnableRequest,
    session: CurrentActiveSession,
    db: DBSession,
) -> RecoveryCodesResponse:
    """
    Verify the OTP code and enable 2FA.
    """
    # Use the TwoFactorService orchestrator to handle enablement and recovery codes
    codes = await TwoFactorService.enable(
        db=db,
        user=session.user,
        code=data.code,
        method="otp",
    )

    return RecoveryCodesResponse(
        message=T("auth:otp_enabled_successfully"),
        data=RecoveryCodesData(recovery_codes=codes),
    )


@router.post(
    "/disable",
    response_model=BaseResponseModel[None],
)
async def disable_otp(
    data: TwoFactorDisableRequest,
    session: CurrentActiveSession,
    db: DBSession,
) -> BaseResponseModel[None]:
    """
    Disable OTP two-factor authentication.
    """
    await TwoFactorService.disable(
        db=db,
        user=session.user,
        password=data.password,
        code=data.code,
    )

    return BaseResponseModel(
        message=T("auth:otp_disabled_successfully"),
    )
