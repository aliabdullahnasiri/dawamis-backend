from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.context.database import reset_db, set_db
from app.extensions.db import SessionLocal


class DatabaseMiddleware(BaseHTTPMiddleware):
    """
    Create and manage a database session for each HTTP request.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """
        Create a database session and make it available
        through the request context.
        """
        db = SessionLocal()
        token = set_db(db)

        try:
            response = await call_next(request)

            db.commit()

            return response

        except Exception:
            db.rollback()
            raise

        finally:
            reset_db(token)
            db.close()
