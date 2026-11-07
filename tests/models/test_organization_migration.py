"""Exercise the new migration against a legacy SQLite schema and persisted data."""

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_upgrade_and_downgrade():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic/versions/72c8b9e15a20_organization_context.py"
    )
    spec = importlib.util.spec_from_file_location("organization_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE users (id INTEGER PRIMARY KEY)")
        connection.exec_driver_sql(
            "CREATE TABLE organizations (id INTEGER PRIMARY KEY, name VARCHAR(150))"
        )
        connection.exec_driver_sql(
            "CREATE TABLE user_sessions (id INTEGER PRIMARY KEY)"
        )
        connection.exec_driver_sql("INSERT INTO organizations VALUES (1, 'Legacy')")
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            row = connection.exec_driver_sql(
                "SELECT owner_id, settings FROM organizations"
            ).one()
            assert row == (None, "{}")
            assert {
                column["name"]
                for column in sa.inspect(connection).get_columns("user_sessions")
            } == {"id", "organization_id"}
            migration.downgrade()
            assert connection.exec_driver_sql("SELECT * FROM organizations").one() == (
                1,
                "Legacy",
            )
    engine.dispose()
