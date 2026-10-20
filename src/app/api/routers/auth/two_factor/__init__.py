# Combined router for 2FA
from app.api.router import Router

from .otp.router import router as otp_router
from .totp.router import router as totp_router
from .verification import router as verification_router

router = Router(prefix="/2fa", tags=["Authentication - Two Factor"])

router.include_router(otp_router)
router.include_router(totp_router)
router.include_router(verification_router)
