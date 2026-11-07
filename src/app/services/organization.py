from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.core.i18n.types import T
from app.models import (
    Branch,
    Organization,
    OrganizationUser,
    Permission,
    RolePermission,
    User,
    UserRole,
    UserSession,
)


class OrganizationService:
    """
    Provides business logic for organization and branch management.

    This service handles organization creation, retrieval, membership management,
    and branch coordination.
    """

    @staticmethod
    async def create(
        db: AsyncSession,
        name: str,
        slug: str,
        owner: User | None = None,
        settings: dict | None = None,
    ) -> Organization:
        """
        Create a new organization.
        """
        # Check if slug already exists
        existing = (
            await db.execute(select(Organization).where(Organization.slug == slug))
        ).scalar_one_or_none()

        if existing:
            raise ConflictError(message=T("organization:slug_already_exists"))

        organization = Organization(
            name=name,
            slug=slug,
            owner_id=owner.id if owner else None,
            settings=settings or {},
        )

        db.add(organization)
        if owner:
            organization.memberships = [OrganizationUser(user_id=owner.id)]
        await OrganizationService.commit(db)
        await db.refresh(organization)

        return organization

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        organization_id: int,
    ) -> Organization:
        """
        Return an organization by its ID.
        """
        organization = (
            await db.execute(
                select(Organization).where(Organization.id == organization_id)
            )
        ).scalar_one_or_none()

        if organization is None:
            raise NotFoundError(message=T("organization:not_found"))

        return organization

    @staticmethod
    async def get_by_uuid(
        db: AsyncSession,
        organization_uuid: UUID,
    ) -> Organization:
        """
        Return an organization by its UUID.
        """
        organization = (
            await db.execute(
                select(Organization).where(Organization.uuid == organization_uuid)
            )
        ).scalar_one_or_none()

        if organization is None:
            raise NotFoundError(message=T("organization:not_found"))

        return organization

    @staticmethod
    async def get_by_slug(
        db: AsyncSession,
        slug: str,
    ) -> Organization:
        """
        Return an organization by its slug.
        """
        organization = (
            await db.execute(select(Organization).where(Organization.slug == slug))
        ).scalar_one_or_none()

        if organization is None:
            raise NotFoundError(message=T("organization:not_found"))

        return organization

    @staticmethod
    async def update(
        db: AsyncSession,
        organization: Organization,
        name: str | None = None,
        slug: str | None = None,
        is_active: bool | None = None,
        settings: dict | None = None,
        owner_id: int | None = None,
    ) -> Organization:
        """
        Update organization details.
        """
        if slug and slug != organization.slug:
            existing = (
                await db.execute(select(Organization).where(Organization.slug == slug))
            ).scalar_one_or_none()
            if existing:
                raise ConflictError(message=T("organization:slug_already_exists"))
            organization.slug = slug

        if name is not None:
            organization.name = name

        if is_active is not None:
            organization.is_active = is_active

        if settings is not None:
            organization.settings = settings
        if owner_id is not None:
            owner = await db.get(User, owner_id)
            if owner is None:
                raise NotFoundError(message=T("organization:membership_not_found"))
            await OrganizationService.validate_membership(db, owner, organization)
            organization.owner_id = owner_id
        await OrganizationService.commit(db)
        await db.refresh(organization)
        return organization

    @staticmethod
    async def delete(
        db: AsyncSession,
        organization: Organization,
    ) -> None:
        """
        Delete an organization.
        """
        await db.execute(
            update(UserSession)
            .where(UserSession.organization_id == organization.id)
            .values(organization_id=None)
        )
        await db.execute(
            delete(UserRole).where(UserRole.organization_id == organization.id)
        )
        await db.delete(organization)
        await db.commit()

    @staticmethod
    async def add_member(
        db: AsyncSession,
        organization_id: int,
        user_id: int,
    ) -> OrganizationUser:
        """
        Add a user to an organization.
        """
        await OrganizationService.get_by_id(db, organization_id)
        if await db.get(User, user_id) is None:
            raise NotFoundError(message=T("auth:user_not_found"))
        # Check if membership already exists
        existing = (
            await db.execute(
                select(OrganizationUser).where(
                    OrganizationUser.organization_id == organization_id,
                    OrganizationUser.user_id == user_id,
                )
            )
        ).scalar_one_or_none()

        if existing:
            return existing

        membership = OrganizationUser(
            organization_id=organization_id,
            user_id=user_id,
        )
        db.add(membership)
        await OrganizationService.commit(db)
        await db.refresh(membership)
        return membership

    @staticmethod
    async def remove_member(
        db: AsyncSession,
        organization_id: int,
        user_id: int,
    ) -> None:
        """
        Remove a user from an organization.
        """
        membership = (
            await db.execute(
                select(OrganizationUser).where(
                    OrganizationUser.organization_id == organization_id,
                    OrganizationUser.user_id == user_id,
                )
            )
        ).scalar_one_or_none()

        if membership:
            organization = await OrganizationService.get_by_id(db, organization_id)
            if organization.owner_id == user_id:
                raise ConflictError(message=T("organization:owner_membership_required"))
            await OrganizationService.clear_member_access(db, organization_id, user_id)
            await db.delete(membership)
            await db.commit()

    @staticmethod
    async def validate_membership(
        db: AsyncSession,
        user: User,
        organization: Organization,
    ) -> OrganizationUser:
        """
        Verify that a user is an active member of an organization.

        Raises:
            NotFoundError: If the membership does not exist or is inactive.
        """
        membership = (
            await db.execute(
                select(OrganizationUser).where(
                    OrganizationUser.user_id == user.id,
                    OrganizationUser.organization_id == organization.id,
                    OrganizationUser.is_active == True,
                )
            )
        ).scalar_one_or_none()

        if membership is None:
            raise NotFoundError(message=T("organization:membership_not_found"))

        return membership

    @staticmethod
    async def create_branch(
        db: AsyncSession,
        organization_id: int,
        name: str,
        address: str | None = None,
    ) -> Branch:
        """
        Create a branch for an organization.
        """
        # Ensure organization exists
        await OrganizationService.get_by_id(db, organization_id)

        branch = Branch(
            organization_id=organization_id,
            name=name,
            address=address,
        )
        db.add(branch)
        await db.commit()
        await db.refresh(branch)
        return branch

    @staticmethod
    async def get_branch_by_id(
        db: AsyncSession,
        branch_id: int,
    ) -> Branch:
        """
        Return a branch by its ID.
        """
        branch = (
            await db.execute(select(Branch).where(Branch.id == branch_id))
        ).scalar_one_or_none()

        if branch is None:
            raise NotFoundError(message=T("branch:not_found"))

        return branch

    @staticmethod
    async def update_branch(
        db: AsyncSession,
        branch: Branch,
        name: str | None = None,
        address: str | None = None,
        is_active: bool | None = None,
    ) -> Branch:
        """
        Update branch details.
        """
        if name is not None:
            branch.name = name
        if address is not None:
            branch.address = address
        if is_active is not None:
            branch.is_active = is_active

        await db.commit()
        await db.refresh(branch)
        return branch

    @staticmethod
    async def delete_branch(
        db: AsyncSession,
        branch: Branch,
    ) -> None:
        """
        Delete a branch.
        """
        await db.delete(branch)
        await db.commit()

    @staticmethod
    async def commit(db: AsyncSession) -> None:
        """Map concurrent uniqueness conflicts to a stable domain error."""
        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise ConflictError(message=T("organization:conflict")) from exc

    @staticmethod
    async def list_for_user(
        db: AsyncSession, user: User, offset: int, limit: int
    ) -> list[Organization]:
        """List only organizations with an active membership."""
        return list(
            (
                await db.scalars(
                    select(Organization)
                    .join(OrganizationUser)
                    .where(
                        OrganizationUser.user_id == user.id,
                        OrganizationUser.is_active.is_(True),
                    )
                    .order_by(Organization.id)
                    .offset(offset)
                    .limit(limit)
                )
            ).all()
        )

    @staticmethod
    async def require_permissions(
        db: AsyncSession,
        user_id: int,
        organization_id: int,
        permissions: tuple[str, ...],
    ) -> None:
        """Require every named permission from roles in this organization only."""
        granted = set(
            (
                await db.scalars(
                    select(Permission.name)
                    .join(
                        RolePermission,
                        RolePermission.permission_id == Permission.id,
                    )
                    .join(UserRole, UserRole.role_id == RolePermission.role_id)
                    .where(
                        UserRole.user_id == user_id,
                        UserRole.organization_id == organization_id,
                    )
                )
            ).all()
        )
        if not set(permissions).issubset(granted):
            raise AuthorizationError()

    @staticmethod
    async def authorize_by_uuid(
        db: AsyncSession,
        user: User,
        organization_uuid: UUID,
        permission: str | None = None,
    ) -> Organization:
        """Resolve a public UUID before authorizing with internal primary keys."""
        organization = await OrganizationService.get_by_uuid(db, organization_uuid)
        return await OrganizationService.authorize(
            db, user, organization.id, permission
        )

    @staticmethod
    async def authorize(
        db: AsyncSession,
        user: User,
        organization_id: int,
        permission: str | None = None,
    ) -> Organization:
        """Check membership before granting read or administrative access."""
        if permission:
            organization = await db.scalar(
                select(Organization)
                .where(Organization.id == organization_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if organization is None:
                raise NotFoundError(message=T("organization:not_found"))
        else:
            organization = await OrganizationService.get_by_id(db, organization_id)
        await OrganizationService.validate_membership(db, user, organization)
        if permission and organization.owner_id != user.id:
            if not organization.is_active:
                raise AuthorizationError()
            await OrganizationService.require_permissions(
                db, user.id, organization_id, (permission,)
            )
        return organization

    @staticmethod
    async def select(
        db: AsyncSession, session: UserSession, organization_id: int
    ) -> Organization:
        """Persist organization selection on this device's authenticated session."""
        organization = await OrganizationService.authorize(
            db, session.user, organization_id
        )
        if not organization.is_active:
            raise AuthorizationError()
        session.organization_id = organization.id
        await db.commit()
        return organization

    @staticmethod
    async def members(
        db: AsyncSession, organization_id: int, offset: int, limit: int
    ) -> list[OrganizationUser]:
        """Return a bounded page of memberships."""
        return list(
            (
                await db.scalars(
                    select(OrganizationUser)
                    .where(
                        OrganizationUser.organization_id == organization_id,
                    )
                    .order_by(OrganizationUser.id)
                    .offset(offset)
                    .limit(limit)
                )
            ).all()
        )

    @staticmethod
    async def get_member_by_uuid(
        db: AsyncSession, organization_id: int, member_uuid: UUID
    ) -> OrganizationUser:
        """Look up a membership without crossing tenant boundaries."""
        membership = await db.scalar(
            select(OrganizationUser).where(
                OrganizationUser.uuid == member_uuid,
                OrganizationUser.organization_id == organization_id,
            )
        )
        if membership is None:
            raise NotFoundError(message=T("organization:membership_not_found"))
        return membership

    @staticmethod
    async def clear_member_access(
        db: AsyncSession, organization_id: int, user_id: int
    ) -> None:
        """Remove role grants and selected contexts when membership is removed."""
        await db.execute(
            delete(UserRole).where(
                UserRole.organization_id == organization_id, UserRole.user_id == user_id
            )
        )
        await db.execute(
            update(UserSession)
            .where(
                UserSession.organization_id == organization_id,
                UserSession.user_id == user_id,
            )
            .values(organization_id=None)
        )

    @staticmethod
    async def update_member(
        db: AsyncSession,
        organization: Organization,
        membership: OrganizationUser,
        is_active: bool,
    ) -> OrganizationUser:
        """Change membership status while protecting the owner."""
        if not is_active and membership.user_id == organization.owner_id:
            raise ConflictError(message=T("organization:owner_membership_required"))
        membership.is_active = is_active
        if not is_active:
            await db.execute(
                update(UserSession)
                .where(
                    UserSession.organization_id == organization.id,
                    UserSession.user_id == membership.user_id,
                )
                .values(organization_id=None)
            )
        await db.commit()
        return membership
