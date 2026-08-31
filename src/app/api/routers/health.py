from typing import Union

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.api.dependencies import DBSession
from app.core.i18n.types import LazyStr
from app.models import user

router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get("/")
def health_check(db: DBSession) -> dict[str, str]:
    """
    Check whether the application and database are healthy.

    Returns:
        dict[str, str]: A response containing the application's health status.

    Raises:
        HTTPException: If the database connection is unavailable.
    """

    try:
        db.execute(text("SELECT version()"))

    except Exception:
        raise HTTPException(
            status_code=503,
            detail=LazyStr("health.database_unavailable"),
        )

    return {"status": LazyStr("health.ok")}
