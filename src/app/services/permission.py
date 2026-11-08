import json

from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.permissions import PERMISSION_DEFINITIONS
from app.models import Organization, Permission, Role, RolePermission, UserRole


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

    @staticmethod
    async def list_definitions(db: AsyncSession) -> list[Permission]:
        """Return the registered catalog, including names declared by dependencies."""
        await PermissionService.ensure_exists(db, PERMISSION_DEFINITIONS)
        return list(
            (await db.scalars(select(Permission).order_by(Permission.name))).all()
        )

    @staticmethod
    async def invalidate(db: AsyncSession, organization_id: int) -> None:
        """Advance the cache namespace atomically with an authorization change."""
        await db.execute(
            update(Organization)
            .where(Organization.id == organization_id)
            .values(rbac_version=Organization.rbac_version + 1)
        )

    @staticmethod
    async def granted(
        db: AsyncSession,
        user_id: int,
        organization_id: int,
        redis: Redis | None = None,
    ) -> set[str]:
        """Cache only scoped grants; callers must revalidate membership and ownership."""
        version = await db.scalar(
            select(Organization.rbac_version).where(Organization.id == organization_id)
        )
        key = f"rbac:permissions:{organization_id}:{version}:{user_id}"
        if redis is not None:
            try:
                cached = await redis.get(key)
                if cached is not None:
                    names = json.loads(cached)
                    if isinstance(names, list) and all(
                        isinstance(name, str) for name in names
                    ):
                        return set(names)
            except RedisError, ValueError, TypeError:
                # Redis is an optimization; the database remains authoritative.
                pass

        granted = set(
            (
                await db.scalars(
                    select(Permission.name)
                    .join(RolePermission, RolePermission.permission_id == Permission.id)
                    .join(Role, Role.id == RolePermission.role_id)
                    .join(UserRole, UserRole.role_id == Role.id)
                    .where(
                        UserRole.user_id == user_id,
                        UserRole.organization_id == organization_id,
                        Role.organization_id == organization_id,
                    )
                )
            ).all()
        )
        if redis is not None:
            try:
                await redis.set(
                    key,
                    json.dumps(sorted(granted)),
                    ex=settings.PERMISSION_CACHE_TTL_SECONDS,
                )
            except RedisError:
                pass
        return granted
