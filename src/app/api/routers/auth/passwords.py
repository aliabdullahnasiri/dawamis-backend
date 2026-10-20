from app.api.dependencies.auth import CurrentActiveSession
from app.api.dependencies.db import DBSession
from app.api.router import Router
from app.core.i18n.types import T
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.schemas.auth import PasswordResetResponse
from app.services.auth import AuthService
from app.services.auth.password_reset import PasswordResetService

router = Router(tags=["Authentication - Passwords"])

@router.post(
    "/password/forgot",
    response_model=PasswordResetResponse,
)
async def password_forgot(
    data: ForgotPasswordRequest,
    db: DBSession,
) -> PasswordResetResponse:
    """
    Request a password reset email.
    """
    await PasswordResetService.send_reset_email(
        db=db,
        email=data.email,
    )

    return PasswordResetResponse(
        message=T("auth:password_reset_email_sent"),
    )


@router.post(
    "/password/reset",
    response_model=PasswordResetResponse,
)
async def password_reset(
    data: ResetPasswordRequest,
    db: DBSession,
) -> PasswordResetResponse:
    """
    Reset password using a secure token.
    """
    await PasswordResetService.reset_password(
        db=db,
        token=data.token,
        new_password=data.new_password,
    )

    return PasswordResetResponse(
        message=T("auth:password_reset_successful"),
    )


@router.post(
    "/password/change",
    response_model=PasswordResetResponse,
)
async def password_change(
    data: ChangePasswordRequest,
    session: CurrentActiveSession,
    db: DBSession,
) -> PasswordResetResponse:
    """
    Change password while authenticated.
    """
    from app.services.user import UserService
    user = await UserService.get_by_uuid(
        db=db,
        user_uuid=session.user.uuid,
    )

    await AuthService.change_password(
        db=db,
        user=user,
        current_password=data.current_password,
        new_password=data.new_password,
    )

    return PasswordResetResponse(
        message=T("auth:password_change_successful"),
    )
