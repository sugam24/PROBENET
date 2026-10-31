"""add canonical ping uniqueness

Revision ID: 027469e4edd6
Revises: 83264759e687
Create Date: 2026-10-31 16:17:13.351032

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '027469e4edd6'
down_revision: Union[str, Sequence[str], None] = '83264759e687'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Prevent duplicate canonical ping observations."""

    op.create_unique_constraint(
        "uq_fact_ping_logical_event",
        "fact_ping",
        [
            "measurement_id",
            "probe_id",
            "event_time",
        ],
    )

    op.create_unique_constraint(
        "uq_fact_ping_raw_result",
        "fact_ping",
        ["raw_result_id"],
    )


def downgrade() -> None:
    """Remove canonical ping uniqueness constraints."""

    op.drop_constraint(
        "uq_fact_ping_raw_result",
        "fact_ping",
        type_="unique",
    )

    op.drop_constraint(
        "uq_fact_ping_logical_event",
        "fact_ping",
        type_="unique",
    )