"""Archer per-tournament scan queue

Revision ID: 004
Revises: 003
Create Date: 2026-05-17

"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "archer_scan_queue_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("tournament_name", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_archer_scan_queue_items_user_id"),
        "archer_scan_queue_items",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_archer_scan_queue_items_tournament_id"),
        "archer_scan_queue_items",
        ["tournament_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f("ix_archer_scan_queue_items_tournament_id"),
        table_name="archer_scan_queue_items",
    )
    op.drop_index(
        op.f("ix_archer_scan_queue_items_user_id"),
        table_name="archer_scan_queue_items",
    )
    op.drop_table("archer_scan_queue_items")
