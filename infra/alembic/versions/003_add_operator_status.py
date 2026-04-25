"""003 — Add operator_status column to events table.

Revision ID: 003_add_operator_status
Revises: 002_add_plate_number
Create Date: 2026-04-25

Adds an operator workflow status field so operators can mark events as
pending, reviewed, or dismissed.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_add_operator_status"
down_revision: Union[str, None] = "002_add_plate_number"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("events")]
    if "operator_status" not in columns:
        op.add_column(
            "events",
            sa.Column(
                "operator_status",
                sa.String(20),
                nullable=False,
                server_default="pending",
            ),
        )


def downgrade() -> None:
    op.drop_column("events", "operator_status")
