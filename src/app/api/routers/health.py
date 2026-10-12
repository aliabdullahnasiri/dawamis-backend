from sqlalchemy import text

from app.api.dependencies import DBSession
from app.api.dependencies.auth import CurrentActiveSession
from app.api.router import Router
from app.core.exceptions import ServiceUnavailableError
from app.core.i18n.types import T

router = Router(
    prefix="/health",
    tags=["Health"],
)


@router.get("/")
async def health_check(
    db: DBSession,
    session: CurrentActiveSession,
) -> dict[str, str]:
    """
    Check whether the application and database are healthy.

    Returns:
        dict[str, str]: A response containing the application's health status.

    Raises:
        ServiceUnavailableError: If the database connection is unavailable.
    """

    try:
        await db.execute(text("SELECT 1"))

    except Exception:
        raise ServiceUnavailableError()

    return {"status": T("health.ok")}
