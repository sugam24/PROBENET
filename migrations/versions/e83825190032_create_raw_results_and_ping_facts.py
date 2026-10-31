"""create raw results and ping facts

Revision ID: e83825190032
Revises: 
Create Date: 2026-10-31 14:15:27.891302

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e83825190032'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create raw ingestion and normalized ping tables."""

    op.create_table(
        "raw_results",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(),
            primary_key=True,
        ),
        sa.Column("measurement_id", sa.Integer(), nullable=False),
        sa.Column("probe_id", sa.Integer(), nullable=False),
        sa.Column(
            "event_time",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "payload",
            postgresql.JSONB(),
            nullable=False,
        ),
        sa.Column(
            "payload_hash",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "persisted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "fact_ping",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(),
            primary_key=True,
        ),
        sa.Column(
            "raw_result_id",
            sa.BigInteger(),
            sa.ForeignKey("raw_results.id"),
            nullable=False,
        ),
        sa.Column("measurement_id", sa.Integer(), nullable=False),
        sa.Column("probe_id", sa.Integer(), nullable=False),
        sa.Column(
            "event_time",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("address_family", sa.SmallInteger()),
        sa.Column("packets_sent", sa.Integer(), nullable=False),
        sa.Column("packets_received", sa.Integer(), nullable=False),
        sa.Column("packet_loss_ratio", sa.Float()),
        sa.Column("average_rtt_ms", sa.Float()),
        sa.Column("minimum_rtt_ms", sa.Float()),
        sa.Column("maximum_rtt_ms", sa.Float()),
        sa.CheckConstraint(
            "packets_sent >= 0 AND packets_received >= 0 "
            "AND packets_received <= packets_sent",
            name="ck_fact_ping_packet_counts",
        ),
        sa.CheckConstraint(
            "packet_loss_ratio IS NULL OR "
            "(packet_loss_ratio >= 0 AND packet_loss_ratio <= 1)",
            name="ck_fact_ping_loss_ratio",
        ),
        sa.CheckConstraint(
            "address_family IS NULL OR address_family IN (4, 6)",
            name="ck_fact_ping_address_family",
        ),
        sa.CheckConstraint(
            "packets_received <> 0 OR average_rtt_ms IS NULL",
            name="ck_fact_ping_no_reply_avg",
        ),
    )


def downgrade() -> None:
    """Remove ping tables in reverse dependency order."""

    op.drop_table("fact_ping")
    op.drop_table("raw_results")
