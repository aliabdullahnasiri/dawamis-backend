from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.api.dependencies import DBSession
from app.api.dependencies.auth import CurrentActiveSession
from app.core.i18n.types import T

router = APIRouter(
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
        HTTPException: If the database connection is unavailable.
    """

    try:
        await db.execute(text("SELECT 1"))

    except Exception:
        raise HTTPException(
            status_code=503,
            detail=T("health.database_unavailable"),
        )

    return {"status": T("health.ok")}
