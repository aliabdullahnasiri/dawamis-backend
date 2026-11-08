"""Exercise tenant cloning and a downgrade that never merges distinct grants."""

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_rbac_migration_preserves_and_isolates_legacy_grants():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic/versions/a9c4e8b27110_organization_rbac.py"
    )
    spec = importlib.util.spec_from_file_location("rbac_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            for statement in (
                "CREATE TABLE organizations (id INTEGER PRIMARY KEY)",
                "CREATE TABLE roles (id INTEGER PRIMARY KEY, uuid CHAR(32) NOT NULL UNIQUE, name VARCHAR(50) NOT NULL, description VARCHAR(255), is_system BOOLEAN NOT NULL, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL)",
                "CREATE UNIQUE INDEX ix_roles_name ON roles(name)",
                "CREATE TABLE permissions (id INTEGER PRIMARY KEY)",
                "CREATE TABLE role_permissions (id INTEGER PRIMARY KEY, uuid CHAR(32) NOT NULL UNIQUE, role_id INTEGER REFERENCES roles(id), permission_id INTEGER REFERENCES permissions(id), created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL)",
                "CREATE TABLE user_roles (id INTEGER PRIMARY KEY, role_id INTEGER REFERENCES roles(id), organization_id INTEGER REFERENCES organizations(id), user_id INTEGER)",
                "INSERT INTO organizations VALUES (1), (2)",
                "INSERT INTO roles VALUES (1, '00000000000000000000000000000001', 'Staff', 'Legacy description', 0, '2026-01-01', '2026-01-01'), (2, '00000000000000000000000000000002', 'Unassigned', NULL, 1, '2026-01-01', '2026-01-01')",
                "INSERT INTO permissions VALUES (1)",
                "INSERT INTO role_permissions VALUES (1, '00000000000000000000000000000003', 1, 1, '2026-01-01', '2026-01-01')",
                "INSERT INTO user_roles VALUES (1, 1, 1, 10), (2, 1, 2, 20)",
            ):
                connection.exec_driver_sql(statement)
            with Operations.context(MigrationContext.configure(connection)):
                migration.upgrade()
                scoped = connection.exec_driver_sql(
                    "SELECT id, organization_id, name, description FROM roles WHERE organization_id IS NOT NULL ORDER BY organization_id"
                ).all()
                assert len(scoped) == 2
                assert scoped[0][1:] == (1, "Staff", "Legacy description")
                assert scoped[1][1:] == (2, "Staff", "Legacy description")
                assignments = connection.exec_driver_sql(
                    "SELECT role_id, organization_id FROM user_roles ORDER BY organization_id"
                ).all()
                assert assignments == [(scoped[0][0], 1), (scoped[1][0], 2)]
                assert (
                    connection.exec_driver_sql(
                        "SELECT count(*) FROM role_permissions"
                    ).scalar()
                    == 3
                )
                assert (
                    connection.exec_driver_sql(
                        "SELECT count(*) FROM roles WHERE organization_id IS NULL"
                    ).scalar()
                    == 2
                )
                assert connection.exec_driver_sql(
                    "SELECT rbac_version FROM organizations"
                ).all() == [(0,), (0,)]
                # Changing one clone must not affect the other organization.
                connection.execute(
                    sa.text("DELETE FROM role_permissions WHERE role_id = :id"),
                    {"id": scoped[0][0]},
                )
                assert (
                    connection.execute(
                        sa.text(
                            "SELECT count(*) FROM role_permissions WHERE role_id = :id"
                        ),
                        {"id": scoped[1][0]},
                    ).scalar()
                    == 1
                )
                migration.downgrade()
                assert (
                    connection.exec_driver_sql(
                        "SELECT role_id, organization_id FROM user_roles ORDER BY organization_id"
                    ).all()
                    == assignments
                )
                names = (
                    connection.exec_driver_sql("SELECT name FROM roles").scalars().all()
                )
                assert len(names) == len(set(names)) == 4
                assert (
                    connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
                )
    finally:
        engine.dispose()
