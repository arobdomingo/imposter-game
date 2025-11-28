"""Add current_jwt to users

Revision ID: c97cebbff09a
Revises: ee74f6dc0d03
Create Date: 2025-11-27 13:03:33.649191

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c97cebbff09a'
down_revision: Union[str, Sequence[str], None] = 'ee74f6dc0d03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('current_jwt', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'current_jwt')
