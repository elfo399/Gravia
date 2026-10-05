"""Profiles, measurement sessions, and final measurements."""

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "profiles",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("height_cm", sa.Float()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "measurement_sessions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("profile_id", sa.String(), sa.ForeignKey("profiles.id"), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime()),
        sa.Column("error_message", sa.String()),
    )
    op.create_index("ix_measurement_sessions_profile_id", "measurement_sessions", ["profile_id"])
    op.create_table(
        "measurements",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(),
            sa.ForeignKey("measurement_sessions.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("profile_id", sa.String(), sa.ForeignKey("profiles.id"), nullable=False),
        *[
            sa.Column(name, sa.Float(), nullable=False)
            for name in (
                "weight",
                "front_left",
                "front_right",
                "rear_left",
                "rear_right",
                "center_x",
                "center_y",
                "stability",
            )
        ],
        sa.Column("measured_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("notes", sa.String()),
    )
    op.create_index("ix_measurements_profile_id", "measurements", ["profile_id"])
    op.create_index("ix_measurements_measured_at", "measurements", ["measured_at"])


def downgrade():
    op.drop_table("measurements")
    op.drop_table("measurement_sessions")
    op.drop_table("profiles")
