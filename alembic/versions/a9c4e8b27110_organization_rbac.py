"""Scope roles to organizations and version permission caches.

Legacy roles are retained as unassignable templates. Each organization with an
existing assignment receives an independent copy, including its permissions.
"""

from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision = "a9c4e8b27110"
down_revision = "576b5739eed4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("rbac_version", sa.Integer(), nullable=False, server_default="0"),
    )
    with op.batch_alter_table("roles") as batch:
        batch.drop_index("ix_roles_name")
        batch.add_column(sa.Column("organization_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_roles_organization",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch.create_index("ix_roles_name", ["name"], unique=False)
        batch.create_index("ix_roles_organization_id", ["organization_id"])
        batch.create_unique_constraint(
            "uq_role_organization_name", ["organization_id", "name"]
        )

    connection = op.get_bind()
    metadata = sa.MetaData()
    roles = sa.Table("roles", metadata, autoload_with=connection)
    grants = sa.Table("role_permissions", metadata, autoload_with=connection)
    assignments = sa.Table("user_roles", metadata, autoload_with=connection)
    pairs = connection.execute(
        sa.select(assignments.c.role_id, assignments.c.organization_id).distinct()
    ).all()
    for role_id, organization_id in pairs:
        original = dict(
            connection.execute(sa.select(roles).where(roles.c.id == role_id))
            .mappings()
            .one()
        )
        original.pop("id")
        original.update(uuid=uuid4().hex, organization_id=organization_id)
        result = connection.execute(roles.insert().values(**original))
        new_id = result.inserted_primary_key[0]
        for grant in (
            connection.execute(sa.select(grants).where(grants.c.role_id == role_id))
            .mappings()
            .all()
        ):
            copied = dict(grant)
            copied.pop("id")
            copied.update(uuid=uuid4().hex, role_id=new_id)
            connection.execute(grants.insert().values(**copied))
        connection.execute(
            assignments.update()
            .where(
                assignments.c.role_id == role_id,
                assignments.c.organization_id == organization_id,
            )
            .values(role_id=new_id)
        )


def downgrade() -> None:
    # Keep independent role grants: merging same-named roles could escalate access.
    connection = op.get_bind()
    roles = sa.table(
        "roles", sa.column("id", sa.Integer()), sa.column("name", sa.String(50))
    )
    rows = connection.execute(sa.select(roles).order_by(roles.c.id)).all()
    for role_id, name in rows:
        # Use the database's collation, including MySQL's case/accent equality.
        duplicate = connection.scalar(
            sa.select(roles.c.id)
            .where(roles.c.name == name, roles.c.id < role_id)
            .limit(1)
        )
        if duplicate is not None:
            suffix = f"-{role_id}"
            candidate = name[: 50 - len(suffix)] + suffix
            while (
                connection.scalar(
                    sa.select(roles.c.id)
                    .where(roles.c.name == candidate, roles.c.id != role_id)
                    .limit(1)
                )
                is not None
            ):
                suffix += "x"
                candidate = name[: 50 - len(suffix)] + suffix
            connection.execute(
                roles.update().where(roles.c.id == role_id).values(name=candidate)
            )
    with op.batch_alter_table("roles") as batch:
        batch.drop_constraint("uq_role_organization_name", type_="unique")
        batch.drop_constraint("fk_roles_organization", type_="foreignkey")
        batch.drop_index("ix_roles_organization_id")
        batch.drop_index("ix_roles_name")
        batch.drop_column("organization_id")
        batch.create_index("ix_roles_name", ["name"], unique=True)
    op.drop_column("organizations", "rbac_version")
