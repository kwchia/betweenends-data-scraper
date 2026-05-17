"""Add saved tournaments library table

Revision ID: 002
Revises: 001
Create Date: 2026-05-16

"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "saved_tournaments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("club_id", sa.Integer(), nullable=True),
        sa.Column("tournament_name", sa.String(length=512), nullable=False),
        sa.Column("location", sa.String(length=512), nullable=True),
        sa.Column("start_date", sa.String(length=32), nullable=True),
        sa.Column("end_date", sa.String(length=32), nullable=True),
        sa.Column("club_name", sa.String(length=255), nullable=False),
        sa.Column("snapshot_json", sa.JSON(), nullable=False),
        sa.Column("saved_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["clubs.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "tournament_id", "club_id", name="uq_saved_tournament_user_club"
        ),
    )
    op.create_index(
        op.f("ix_saved_tournaments_tournament_id"),
        "saved_tournaments",
        ["tournament_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_saved_tournaments_user_id"), "saved_tournaments", ["user_id"], unique=False
    )


def downgrade():
    op.drop_index(op.f("ix_saved_tournaments_user_id"), table_name="saved_tournaments")
    op.drop_index(op.f("ix_saved_tournaments_tournament_id"), table_name="saved_tournaments")
    op.drop_table("saved_tournaments")
