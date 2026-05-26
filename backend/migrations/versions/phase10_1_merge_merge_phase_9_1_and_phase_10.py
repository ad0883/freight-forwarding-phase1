"""Merge phase 9.1 and phase 10

Revision ID: phase10_1_merge
Revises: phase9_1_gmail_cleanup, phase10_export_import_states
Create Date: 2026-05-26 23:29:32.194088
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'phase10_1_merge'
down_revision: Union[str, None] = ('phase9_1_gmail_cleanup', 'phase10_export_import_states')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
