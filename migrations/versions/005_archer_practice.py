"""Archer manual practice sessions

Revision ID: 005
Revises: 004
Create Date: 2026-05-18

"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "saved_archer_practices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("practice_date", sa.String(length=32), nullable=False),
        sa.Column("include_in_analytics", sa.Boolean(), nullable=False),
        sa.Column("rounds_json", sa.JSON(), nullable=False),
        sa.Column("saved_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_saved_archer_practices_user_id"),
        "saved_archer_practices",
        ["user_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f("ix_saved_archer_practices_user_id"),
        table_name="saved_archer_practices",
    )
    op.drop_table("saved_archer_practices")
