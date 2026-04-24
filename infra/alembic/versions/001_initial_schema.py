"""001 — Initial schema: events and devices tables.

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-04-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("camera_id", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="info"),
        sa.Column("estimated_speed", sa.Float, nullable=True),
        sa.Column("speed_limit", sa.Float, nullable=True),
        sa.Column("fused_speed", sa.Float, nullable=True),
        sa.Column("violation_amount", sa.Float, nullable=True),
        sa.Column("track_id", sa.Integer, nullable=True),
        sa.Column("label", sa.String(100), nullable=True),
        sa.Column("image_evidence_path", sa.Text, nullable=True),
        sa.Column("plate_number", sa.String(20), nullable=True),
        sa.Column("payload", sa.JSON, nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_events_event_type", "events", ["event_type"])
    op.create_index("ix_events_created_at", "events", ["created_at"])
    op.create_index("ix_events_camera_id", "events", ["camera_id"])

    op.create_table(
        "devices",
        sa.Column("device_id", sa.String(100), primary_key=True),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("payload", sa.JSON, nullable=False, server_default="{}"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_index("ix_events_camera_id", table_name="events")
    op.drop_index("ix_events_created_at", table_name="events")
    op.drop_index("ix_events_event_type", table_name="events")
    op.drop_table("events")
    op.drop_table("devices")
