"""create probe and measurement metadata tables

Revision ID: 83264759e687
Revises: e83825190032
Create Date: 2026-10-31 16:05:12.486545

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '83264759e687'
down_revision: Union[str, Sequence[str], None] = 'e83825190032'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create current probe and measurement metadata tables."""

    op.create_table(
        "dim_probe",
        sa.Column(
            "probe_id",
            sa.Integer(),
            primary_key=True,
        ),
        sa.Column(
            "country_code",
            sa.String(length=2),
            nullable=True,
        ),
        sa.Column(
            "asn_v4",
            sa.BigInteger(),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "metadata_updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "dim_measurement",
        sa.Column(
            "measurement_id",
            sa.Integer(),
            primary_key=True,
        ),
        sa.Column(
            "target",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "measurement_type",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "interval_seconds",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "is_public",
            sa.Boolean(),
            nullable=True,
        ),
        sa.Column(
            "metadata_updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "interval_seconds IS NULL OR interval_seconds > 0",
            name="ck_dim_measurement_positive_interval",
        ),
    )


def downgrade() -> None:
    """Remove metadata tables."""
    op.drop_table("dim_measurement")
    op.drop_table("dim_probe")
