"""Verify removing legacy permission codes preserves permissions and role grants."""

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_remove_permission_code_preserves_grants():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic/versions/576b5739eed4_remove_permission_code_column.py"
    )
    spec = importlib.util.spec_from_file_location("permission_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.exec_driver_sql(
                "CREATE TABLE permissions (id INTEGER PRIMARY KEY, "
                "name VARCHAR(100) UNIQUE NOT NULL, code INTEGER NOT NULL)"
            )
            connection.exec_driver_sql(
                "CREATE TABLE role_permissions (role_id INTEGER NOT NULL, "
                "permission_id INTEGER REFERENCES permissions(id))"
            )
            connection.exec_driver_sql("INSERT INTO permissions VALUES (1, 'read', 8)")
            connection.exec_driver_sql("INSERT INTO role_permissions VALUES (2, 1)")
            with Operations.context(MigrationContext.configure(connection)):
                migration.upgrade()
            assert connection.exec_driver_sql("SELECT * FROM permissions").one() == (
                1,
                "read",
            )
            assert connection.exec_driver_sql(
                "SELECT * FROM role_permissions"
            ).one() == (2, 1)
            assert {
                column["name"]
                for column in sa.inspect(connection).get_columns("permissions")
            } == {"id", "name"}
    finally:
        engine.dispose()
