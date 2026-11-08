import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import Permission, RolePermission
from app.services.permission import PermissionService


@pytest.mark.asyncio
async def test_register_permissions_is_idempotent_and_preserves_existing(db_session):
    existing = Permission(name="catalog.read", description="Read catalog")
    db_session.add(existing)
    await db_session.commit()

    names = ("catalog.read", "catalog.write", "catalog.write")
    await PermissionService.ensure_exists(db_session, names)
    await PermissionService.ensure_exists(db_session, names)

    registered = (await db_session.scalars(select(Permission.name))).all()
    assert sorted(registered) == ["catalog.read", "catalog.write"]
    assert existing.description == "Read catalog"
    assert (await db_session.scalars(select(RolePermission))).all() == []


@pytest.mark.asyncio
async def test_register_empty_permissions(db_session):
    await PermissionService.ensure_exists(db_session, ())
    assert (await db_session.scalars(select(Permission))).all() == []


@pytest.mark.asyncio
async def test_registration_survives_subsequent_request_rollback(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'permissions.db'}")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Permission.__table__.create)
        sessions = async_sessionmaker(engine)
        async with sessions() as session:
            await PermissionService.ensure_exists(session, ("stock.read",))
            await session.rollback()
        async with sessions() as session:
            assert (await session.scalars(select(Permission.name))).all() == [
                "stock.read"
            ]
    finally:
        await engine.dispose()
