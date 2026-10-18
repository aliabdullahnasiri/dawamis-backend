from app.api.router import Router

from . import passwords, sessions, two_factor, verification

router = Router(
    prefix="/auth",
    tags=["Authentication"],
)

router.include_router(sessions.router)
router.include_router(passwords.router)
router.include_router(verification.router)
router.include_router(two_factor.router)
