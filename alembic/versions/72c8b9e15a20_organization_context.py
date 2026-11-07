"""Add organization ownership, settings, and session selection.

Legacy organizations retain a null owner: ownership must be assigned explicitly.
"""

import sqlalchemy as sa

from alembic import op

revision = "72c8b9e15a20"
down_revision = "346ec1a26172"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("organizations") as batch:
        batch.add_column(sa.Column("owner_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("settings", sa.JSON(), nullable=True))
        batch.create_foreign_key(
            "fk_organizations_owner", "users", ["owner_id"], ["id"], ondelete="RESTRICT"
        )
        batch.create_index("ix_organizations_owner_id", ["owner_id"])
    table = sa.table("organizations", sa.column("settings", sa.JSON()))
    op.execute(table.update().values(settings={}))
    with op.batch_alter_table("organizations") as batch:
        batch.alter_column("settings", existing_type=sa.JSON(), nullable=False)
    with op.batch_alter_table("user_sessions") as batch:
        batch.add_column(sa.Column("organization_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_user_sessions_organization",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_index("ix_user_sessions_organization_id", ["organization_id"])


def downgrade() -> None:
    with op.batch_alter_table("user_sessions") as batch:
        batch.drop_index("ix_user_sessions_organization_id")
        batch.drop_constraint("fk_user_sessions_organization", type_="foreignkey")
        batch.drop_column("organization_id")
    with op.batch_alter_table("organizations") as batch:
        batch.drop_index("ix_organizations_owner_id")
        batch.drop_constraint("fk_organizations_owner", type_="foreignkey")
        batch.drop_column("owner_id")
        batch.drop_column("settings")
