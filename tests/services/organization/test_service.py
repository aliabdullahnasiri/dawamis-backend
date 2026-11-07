import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models import User
from app.services.organization import OrganizationService


@pytest.mark.asyncio
async def test_create_organization(db_session: AsyncSession):
    name = "Test Pharmacy"
    slug = "test-pharmacy"

    org = await OrganizationService.create(db_session, name, slug)

    assert org.id is not None
    assert org.name == name
    assert org.slug == slug
    assert org.is_active is True


@pytest.mark.asyncio
async def test_create_organization_duplicate_slug(db_session: AsyncSession):
    name1 = "Pharmacy 1"
    slug = "shared-slug"
    await OrganizationService.create(db_session, name1, slug)

    with pytest.raises(ConflictError):
        await OrganizationService.create(db_session, "Pharmacy 2", slug)


@pytest.mark.asyncio
async def test_get_by_id(db_session: AsyncSession):
    org = await OrganizationService.create(db_session, "Test", "test-slug")

    retrieved = await OrganizationService.get_by_id(db_session, org.id)
    assert retrieved.id == org.id
    assert retrieved.slug == "test-slug"


@pytest.mark.asyncio
async def test_get_by_id_not_found(db_session: AsyncSession):
    with pytest.raises(NotFoundError):
        await OrganizationService.get_by_id(db_session, 9999)


@pytest.mark.asyncio
async def test_get_by_uuid(db_session: AsyncSession):
    org = await OrganizationService.create(db_session, "Test", "test-slug")

    retrieved = await OrganizationService.get_by_uuid(db_session, org.uuid)
    assert retrieved.id == org.id


@pytest.mark.asyncio
async def test_get_by_slug(db_session: AsyncSession):
    slug = "unique-slug"
    await OrganizationService.create(db_session, "Test", slug)

    retrieved = await OrganizationService.get_by_slug(db_session, slug)
    assert retrieved.slug == slug


@pytest.mark.asyncio
async def test_update_organization(db_session: AsyncSession):
    org = await OrganizationService.create(db_session, "Old Name", "old-slug")

    updated = await OrganizationService.update(
        db_session, org, name="New Name", slug="new-slug", is_active=False
    )

    assert updated.name == "New Name"
    assert updated.slug == "new-slug"
    assert updated.is_active is False


@pytest.mark.asyncio
async def test_update_organization_duplicate_slug(db_session: AsyncSession):
    org1 = await OrganizationService.create(db_session, "Org 1", "slug-1")
    await OrganizationService.create(db_session, "Org 2", "slug-2")

    with pytest.raises(ConflictError):
        await OrganizationService.update(db_session, org1, slug="slug-2")


@pytest.mark.asyncio
async def test_delete_organization(db_session: AsyncSession):
    org = await OrganizationService.create(db_session, "Test", "test-slug")

    await OrganizationService.delete(db_session, org)

    with pytest.raises(NotFoundError):
        await OrganizationService.get_by_id(db_session, org.id)


@pytest.mark.asyncio
async def test_membership_management(db_session: AsyncSession):
    org = await OrganizationService.create(db_session, "Org", "org-slug")
    user = User(
        first_name="Test",
        last_name="User",
        email="test@ex.com",
        user_name="testu",
        password_hash="fake_hash",
    )
    db_session.add(user)
    await db_session.commit()

    # Add member
    membership = await OrganizationService.add_member(db_session, org.id, user.id)
    assert membership.organization_id == org.id
    assert membership.user_id == user.id
    assert membership.is_active is True

    # Add duplicate member (should return existing)
    duplicate = await OrganizationService.add_member(db_session, org.id, user.id)
    assert duplicate.id == membership.id

    # Validate membership
    validated = await OrganizationService.validate_membership(db_session, user, org)
    assert validated.id == membership.id

    # Remove member
    await OrganizationService.remove_member(db_session, org.id, user.id)
    with pytest.raises(NotFoundError):
        await OrganizationService.validate_membership(db_session, user, org)


@pytest.mark.asyncio
async def test_validate_membership_inactive(db_session: AsyncSession):
    org = await OrganizationService.create(db_session, "Org", "org-slug")
    user = User(
        first_name="Test",
        last_name="User",
        email="test@ex.com",
        user_name="testu",
        password_hash="fake_hash",
    )
    db_session.add(user)
    await db_session.commit()

    membership = await OrganizationService.add_member(db_session, org.id, user.id)
    membership.is_active = False
    await db_session.commit()

    with pytest.raises(NotFoundError):
        await OrganizationService.validate_membership(db_session, user, org)


@pytest.mark.asyncio
async def test_branch_management(db_session: AsyncSession):
    org = await OrganizationService.create(db_session, "Org", "org-slug")

    # Create branch
    branch = await OrganizationService.create_branch(
        db_session, org.id, "Main Branch", "123 St"
    )
    assert branch.id is not None
    assert branch.organization_id == org.id
    assert branch.name == "Main Branch"

    # Get branch
    retrieved = await OrganizationService.get_branch_by_id(db_session, branch.id)
    assert retrieved.id == branch.id

    # Update branch
    updated = await OrganizationService.update_branch(
        db_session, branch, name="New Branch Name"
    )
    assert updated.name == "New Branch Name"

    # Delete branch
    await OrganizationService.delete_branch(db_session, branch)
    with pytest.raises(NotFoundError):
        await OrganizationService.get_branch_by_id(db_session, branch.id)


@pytest.mark.asyncio
async def test_create_branch_invalid_org(db_session: AsyncSession):
    with pytest.raises(NotFoundError):
        await OrganizationService.create_branch(db_session, 9999, "Branch")
