"""Organization-scoped role management and delegation rules."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.i18n.types import T
from app.models import (
    Organization,
    OrganizationUser,
    Permission,
    Role,
    RolePermission,
    UserRole,
)
from app.services.organization import OrganizationService
from app.services.permission import PermissionService


class RoleService:
    @staticmethod
    async def list(
        db: AsyncSession, organization_id: int, offset: int = 0, limit: int = 50
    ) -> list[Role]:
        return list(
            (
                await db.scalars(
                    select(Role)
                    .where(Role.organization_id == organization_id)
                    .order_by(Role.id)
                    .offset(offset)
                    .limit(limit)
                )
            ).all()
        )

    @staticmethod
    async def get(db: AsyncSession, organization_id: int, role_uuid: UUID) -> Role:
        role = await db.scalar(
            select(Role)
            .where(Role.organization_id == organization_id, Role.uuid == role_uuid)
            .execution_options(populate_existing=True)
        )
        if role is None:
            raise NotFoundError(message=T("role:not_found"))
        return role

    @staticmethod
    async def lock(db: AsyncSession, organization_id: int) -> None:
        organization = await db.scalar(
            select(Organization.id)
            .where(Organization.id == organization_id)
            .with_for_update()
        )
        if organization is None:
            raise NotFoundError(message=T("organization:not_found"))

    @staticmethod
    def require_mutable(role: Role) -> None:
        if role.is_system:
            raise ConflictError(message=T("role:system_protected"))

    @staticmethod
    async def commit(db: AsyncSession, organization_id: int) -> None:
        try:
            await PermissionService.invalidate(db, organization_id)
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise ConflictError(message=T("role:conflict")) from exc

    @staticmethod
    async def check_name(
        db: AsyncSession, organization_id: int, name: str, role_id: int | None = None
    ) -> None:
        query = select(Role.id).where(
            Role.organization_id == organization_id, Role.name == name
        )
        if role_id is not None:
            query = query.where(Role.id != role_id)
        if await db.scalar(query) is not None:
            raise ConflictError(message=T("role:conflict"))

    @staticmethod
    async def create(
        db: AsyncSession,
        organization_id: int,
        name: str,
        description: str | None = None,
    ) -> Role:
        await RoleService.lock(db, organization_id)
        await RoleService.check_name(db, organization_id, name)
        role = Role(
            organization_id=organization_id,
            name=name,
            description=description,
            is_system=False,
        )
        db.add(role)
        await RoleService.commit(db, organization_id)
        await db.refresh(role)
        return role

    @staticmethod
    async def update(
        db: AsyncSession, organization_id: int, role_uuid: UUID, changes: dict
    ) -> Role:
        await RoleService.lock(db, organization_id)
        role = await RoleService.get(db, organization_id, role_uuid)
        RoleService.require_mutable(role)
        if "name" in changes:
            await RoleService.check_name(db, organization_id, changes["name"], role.id)
            role.name = changes["name"]
        if "description" in changes:
            role.description = changes["description"]
        await RoleService.commit(db, organization_id)
        await db.refresh(role)
        return role

    @staticmethod
    async def delete(db: AsyncSession, organization_id: int, role_uuid: UUID) -> None:
        await RoleService.lock(db, organization_id)
        role = await RoleService.get(db, organization_id, role_uuid)
        RoleService.require_mutable(role)
        await db.delete(role)
        await RoleService.commit(db, organization_id)

    @staticmethod
    async def permissions(
        db: AsyncSession, organization_id: int, role_uuid: UUID
    ) -> list[Permission]:
        role = await RoleService.get(db, organization_id, role_uuid)
        return list(
            (
                await db.scalars(
                    select(Permission)
                    .join(RolePermission)
                    .where(RolePermission.role_id == role.id)
                    .order_by(Permission.name)
                )
            ).all()
        )

    @staticmethod
    async def set_permissions(
        db: AsyncSession,
        organization_id: int,
        role_uuid: UUID,
        names: list[str],
        actor_id: int,
    ) -> list[Permission]:
        """Replace atomically; a delegate cannot grant permissions they do not hold."""
        await RoleService.lock(db, organization_id)
        role = await RoleService.get(db, organization_id, role_uuid)
        RoleService.require_mutable(role)
        permissions = list(
            (
                await db.scalars(
                    select(Permission)
                    .where(Permission.name.in_(set(names)))
                    .order_by(Permission.name)
                )
            ).all()
        )
        if {permission.name for permission in permissions} != set(names):
            raise ValidationError(message=T("permission:unknown"))
        await OrganizationService.require_permissions(
            db, actor_id, organization_id, tuple(names)
        )
        await db.execute(
            delete(RolePermission).where(RolePermission.role_id == role.id)
        )
        db.add_all(
            [RolePermission(role_id=role.id, permission_id=p.id) for p in permissions]
        )
        await RoleService.commit(db, organization_id)
        return permissions

    @staticmethod
    async def member_roles(
        db: AsyncSession, organization_id: int, member_uuid: UUID
    ) -> list[Role]:
        member = await OrganizationService.get_member_by_uuid(
            db, organization_id, member_uuid
        )
        return list(
            (
                await db.scalars(
                    select(Role)
                    .join(UserRole)
                    .where(
                        Role.organization_id == organization_id,
                        UserRole.organization_id == organization_id,
                        UserRole.user_id == member.user_id,
                    )
                    .order_by(Role.id)
                )
            ).all()
        )

    @staticmethod
    async def set_member_roles(
        db: AsyncSession,
        organization_id: int,
        member_uuid: UUID,
        role_uuids: list[UUID],
        actor_id: int,
    ) -> list[Role]:
        """Replace a member's roles, rejecting foreign roles and inactive memberships."""
        await RoleService.lock(db, organization_id)
        member: OrganizationUser = await OrganizationService.get_member_by_uuid(
            db, organization_id, member_uuid
        )
        if not member.is_active:
            raise ConflictError(message=T("role:inactive_member"))
        roles = list(
            (
                await db.scalars(
                    select(Role)
                    .where(
                        Role.organization_id == organization_id,
                        Role.uuid.in_(set(role_uuids)),
                    )
                    .order_by(Role.id)
                )
            ).all()
        )
        if {role.uuid for role in roles} != set(role_uuids):
            raise NotFoundError(message=T("role:not_found"))
        names = tuple(
            (
                await db.scalars(
                    select(Permission.name)
                    .join(RolePermission)
                    .where(RolePermission.role_id.in_([role.id for role in roles]))
                )
            ).all()
        )
        await OrganizationService.require_permissions(
            db, actor_id, organization_id, names
        )
        await db.execute(
            delete(UserRole).where(
                UserRole.organization_id == organization_id,
                UserRole.user_id == member.user_id,
            )
        )
        db.add_all(
            [
                UserRole(
                    user_id=member.user_id,
                    role_id=role.id,
                    organization_id=organization_id,
                )
                for role in roles
            ]
        )
        await RoleService.commit(db, organization_id)
        return roles
