from app.schemas.base import BaseResponseModel


class EmailVerificationResponse(BaseResponseModel[None]):
    """
    Response schema for successful email verification.
    """


class ResendVerificationEmailResponse(BaseResponseModel[None]):
    """
    Response schema for successfully requesting a new verification email.
    """
