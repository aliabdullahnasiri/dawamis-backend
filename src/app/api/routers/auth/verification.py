from app.api.dependencies.db import DBSession
from app.api.router import Router
from app.core.i18n.types import T
from app.schemas.auth import (
    EmailVerificationResponse,
    ResendVerificationEmailRequest,
    ResendVerificationEmailResponse,
    VerifyEmailRequest,
)
from app.services.auth.email_verification import EmailVerificationService
from app.services.user import UserService

router = Router(tags=["Authentication - Verification"])


@router.post(
    "/email/verify",
    response_model=EmailVerificationResponse,
)
async def verify_email(
    data: VerifyEmailRequest,
    db: DBSession,
) -> EmailVerificationResponse:
    await EmailVerificationService.verify(
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
async def resend_verification_email(
    data: ResendVerificationEmailRequest,
    db: DBSession,
) -> ResendVerificationEmailResponse:
    try:
        user = await UserService.get_by_email(db=db, email=data.email)
    except Exception:
        # In a real app, we might return 404 or a generic message for security
        return ResendVerificationEmailResponse(
            message=T("messages:verification_email_sent")
        )

    if not user.is_email_verified:
        await EmailVerificationService.send(db=db, user=user)

    return ResendVerificationEmailResponse(
        message=T("messages:verification_email_sent")
    )
