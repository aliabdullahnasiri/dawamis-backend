from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.i18n.types import T
from app.models import Branch, Organization, OrganizationUser, User


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
        )

        db.add(organization)
        await db.commit()
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

        await db.commit()
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
        await db.commit()
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
