from fastapi import APIRouter, status

from app.api.dependencies.auth import CurrentRefreshToken, CurrentToken, CurrentUserUUID
from app.api.dependencies.db import DBSession
from app.core.i18n.types import T
from app.errors.exceptions import AuthenticationError
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
)
from app.schemas.auth.data import LoginData, RefreshData
from app.schemas.auth.request import (
    ForgotPasswordRequest,
    ResendVerificationEmailRequest,
    VerifyEmailRequest,
    ResetPasswordRequest,
    ChangePasswordRequest,
)
from app.schemas.auth.response import (

    EmailVerificationResponse,
    LogoutResponse,
    RefreshResponse,
    ResendVerificationEmailResponse,
    PasswordResetResponse,
)
from app.schemas.user.data import UserData
from app.services.auth import AuthService
from app.services.email_verification import EmailVerificationService
from app.services.jwt import JWTService
from app.services.password_reset import PasswordResetService
from app.services.user import UserService


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    data: RegisterRequest,
    db: DBSession,
) -> RegisterResponse:
    """
    Register a new user account.
    """
    user = AuthService.register(
        db=db,
        data=data,
    )

    AuthService.send_welcome_email(user)

    return RegisterResponse(
        message=T("auth:registration_successful"),
        data=UserData.model_validate(user),
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
)
def login(
    data: LoginRequest,
    db: DBSession,
) -> LoginResponse:
    """
    Authenticate a user and generate access and refresh tokens.
    """
    user = AuthService.authenticate(
        db=db,
        email=data.email,
        password=data.password,
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
def me(
    user_uuid: CurrentUserUUID,
    db: DBSession,
) -> UserData:
    """
    Return the currently authenticated user.
    """
    user = UserService.get_by_uuid(
        db=db,
        user_uuid=user_uuid,
    )

    return UserData.model_validate(user)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
)
def logout(
    token: CurrentToken,
    db: DBSession,
) -> LogoutResponse:
    """
    Revoke the current access token.
    """
    JWTService.revoke(
        token=token,
        db=db,
    )

    return LogoutResponse(
        message=T("auth:logout_successful"),
    )


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    status_code=status.HTTP_200_OK,
)
def refresh(
    token: CurrentRefreshToken,
    db: DBSession,
) -> RefreshResponse:
    """
    Create a new access token using a valid refresh token.
    """

    claims = JWTService.decode(token)

    if claims.get("type") != "refresh":
        raise AuthenticationError(
            T("auth:invalid_refresh_token"),
        )

    if JWTService.is_revoked(
        token=token,
        db=db,
    ):
        raise AuthenticationError(
            T("auth:token_revoked"),
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


@router.post(
    "/email/verify",
    response_model=EmailVerificationResponse,
)
def verify_email(
    data: VerifyEmailRequest,
    db: DBSession,
) -> EmailVerificationResponse:
    EmailVerificationService.verify(
        db=db,
        token=data.token,
    )

    return EmailVerificationResponse(
        message=T("messages:email_verified_successfully"),
    )


@router.post(
    "/email/resend",
    response_model=ResendVerificationEmailResponse,
)
def resend_verification_email(
    data: ResendVerificationEmailRequest,
    db: DBSession,
) -> ResendVerificationEmailResponse:
    try:
        user: User = UserService.get_by_email(db=db, email=data.email)
    except Exception:
        # In a real app, we might return 404 or a generic message for security
        return ResendVerificationEmailResponse(
            message=T("messages:verification_email_sent")
        )

    if not user.is_email_verified:
        EmailVerificationService.send(db=db, user=user)

    return ResendVerificationEmailResponse(
        message=T("messages:verification_email_sent")
    )


@router.post(
    "/password/forgot",
    response_model=PasswordResetResponse,
)
def password_forgot(
    data: ForgotPasswordRequest,
    db: DBSession,
) -> PasswordResetResponse:
    """
    Request a password reset email.
    """
    PasswordResetService.send_reset_email(
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
def password_reset(
    data: ResetPasswordRequest,
    db: DBSession,
) -> PasswordResetResponse:
    """
    Reset password using a secure token.
    """
    PasswordResetService.reset_password(
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
def password_change(
    data: ChangePasswordRequest,
    user_uuid: CurrentUserUUID,
    db: DBSession,
) -> PasswordResetResponse:
    """
    Change password while authenticated.
    """
    user = UserService.get_by_uuid(
        db=db,
        user_uuid=user_uuid,
    )

    AuthService.change_password(
        db=db,
        user=user,
        current_password=data.current_password,
        new_password=data.new_password,
    )

    return PasswordResetResponse(
        message=T("auth:password_change_successful"),
    )

