"""One software calibration per board, independent of user profiles."""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "board_calibrations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("board_mac", sa.String(), nullable=False),
        *[
            sa.Column(name, sa.Float(), nullable=False)
            for name in (
                "front_left_offset",
                "front_right_offset",
                "rear_left_offset",
                "rear_right_offset",
                "weight_scale",
                "reference_weight",
                "measured_weight_before",
                "measured_weight_after",
            )
        ],
        sa.Column("calibrated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("board_mac"),
    )


def downgrade():
    op.drop_table("board_calibrations")
