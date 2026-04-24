"""002 — Add plate_number column to events table.

Revision ID: 002_add_plate_number
Revises: 001_initial_schema
Create Date: 2026-04-23

Note: plate_number is already included in 001_initial_schema for fresh deployments.
This migration exists for databases that were created before OCR support was added.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_add_plate_number"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # plate_number may already exist if 001 was applied after OCR integration.
    # Use batch_alter_table for safety; skip if column exists.
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("events")]
    if "plate_number" not in columns:
        op.add_column("events", sa.Column("plate_number", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("events", "plate_number")
