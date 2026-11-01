"""add ping measurement time index

Revision ID: e4c4ea2cf8bb
Revises: cab71a5070a6
Create Date: 2026-11-01 16:49:23.002402

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e4c4ea2cf8bb'
down_revision: Union[str, Sequence[str], None] = 'cab71a5070a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Index ping observations by measurement and event time."""
    op.create_index(
        "ix_fact_ping_measurement_event_time",
        "fact_ping",
        ["measurement_id", "event_time"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the measurement-time index."""
    op.drop_index(
        "ix_fact_ping_measurement_event_time",
        table_name="fact_ping",
    )
