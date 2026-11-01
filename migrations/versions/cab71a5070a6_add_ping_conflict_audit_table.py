"""add ping conflict audit table

Revision ID: cab71a5070a6
Revises: 027469e4edd6
Create Date: 2026-11-01 16:07:12.476669

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'cab71a5070a6'
down_revision: Union[str, Sequence[str], None] = '027469e4edd6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the conflict audit table."""

    op.create_table(
        "ping_conflicts",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(),
            primary_key=True,
        ),
        sa.Column(
            "canonical_raw_result_id",
            sa.BigInteger(),
            sa.ForeignKey("raw_results.id"),
            nullable=False,
        ),
        sa.Column(
            "incoming_payload_hash",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "incoming_payload",
            postgresql.JSONB(),
            nullable=False,
        ),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "canonical_raw_result_id",
            "incoming_payload_hash",
            name="uq_ping_conflict_payload",
        ),
    )


def downgrade() -> None:
    """Remove the conflict audit table."""
    op.drop_table("ping_conflicts")
