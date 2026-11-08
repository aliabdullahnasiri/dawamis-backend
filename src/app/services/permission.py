from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Permission


class PermissionService:
    @staticmethod
    async def ensure_exists(db: AsyncSession, permissions: tuple[str, ...]) -> None:
        """Persist missing permission names without assigning them to any role."""
        if not permissions:
            return

        existing = set(
            await db.scalars(
                select(Permission.name).where(Permission.name.in_(permissions))
            )
        )
        missing = set(permissions) - existing
        for name in sorted(missing):
            try:
                # A savepoint keeps a concurrent registration from aborting
                # the request's entire transaction.
                async with db.begin_nested():
                    db.add(Permission(name=name))
                    await db.flush()
            except IntegrityError:
                # Only tolerate an already registered name, not other failures.
                registered = await db.scalar(
                    select(Permission.id)
                    .where(Permission.name == name)
                    .with_for_update()
                )
                if registered is None:
                    raise

        if missing:
            # Keep registrations even when the subsequent access check denies.
            await db.commit()
