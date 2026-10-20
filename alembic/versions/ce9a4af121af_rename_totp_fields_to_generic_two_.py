"""rename totp fields to generic two_factor fields in users table

Revision ID: ce9a4af121af
Revises: 158f487476c1
Create Date: 2026-10-20 09:24:21.044868

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'ce9a4af121af'
down_revision: Union[str, Sequence[str], None] = '158f487476c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # MySQL requires the type to be specified for alter_column (rename)
    op.alter_column('users', 'totp_enabled', new_column_name='two_factor_enabled', type_=sa.Boolean())
    op.alter_column('users', 'totp_secret_encrypted', new_column_name='two_factor_secret_encrypted', type_=sa.String(length=512))
    op.alter_column('users', 'totp_pending_secret_encrypted', new_column_name='two_factor_pending_secret_encrypted', type_=sa.String(length=512))


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('users', 'two_factor_enabled', new_column_name='totp_enabled', type_=sa.Boolean())
    op.alter_column('users', 'two_factor_secret_encrypted', new_column_name='totp_secret_encrypted', type_=sa.String(length=512))
    op.alter_column('users', 'two_factor_pending_secret_encrypted', new_column_name='totp_pending_secret_encrypted', type_=sa.String(length=512))
