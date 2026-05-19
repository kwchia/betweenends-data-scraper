"""Archer mode: profile, library, scan jobs

Revision ID: 003
Revises: 002
Create Date: 2026-05-17

"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("first_name", sa.String(length=128), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(length=128), nullable=True))
    op.add_column(
        "users",
        sa.Column("preferred_mode", sa.String(length=20), nullable=False, server_default="club"),
    )

    op.create_table(
        "archer_name_aliases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_archer_name_aliases_user_id"),
        "archer_name_aliases",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "membership_numbers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("organization", sa.String(length=128), nullable=False),
        sa.Column("number", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_membership_numbers_user_id"),
        "membership_numbers",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "saved_archer_tournaments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("tournament_name", sa.String(length=512), nullable=False),
        sa.Column("location", sa.String(length=512), nullable=True),
        sa.Column("start_date", sa.String(length=32), nullable=True),
        sa.Column("end_date", sa.String(length=32), nullable=True),
        sa.Column("match_reason", sa.String(length=32), nullable=True),
        sa.Column("snapshot_json", sa.JSON(), nullable=False),
        sa.Column("user_metadata", sa.JSON(), nullable=True),
        sa.Column("saved_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "tournament_id", name="uq_saved_archer_tournament_user"
        ),
    )
    op.create_index(
        op.f("ix_saved_archer_tournaments_tournament_id"),
        "saved_archer_tournaments",
        ["tournament_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_saved_archer_tournaments_user_id"),
        "saved_archer_tournaments",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "archer_scan_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("scope", sa.String(length=20), nullable=False),
        sa.Column("progress_current", sa.Integer(), nullable=False),
        sa.Column("progress_total", sa.Integer(), nullable=False),
        sa.Column("tournaments_added", sa.Integer(), nullable=False),
        sa.Column("tournaments_skipped", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_archer_scan_jobs_user_id"),
        "archer_scan_jobs",
        ["user_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_archer_scan_jobs_user_id"), table_name="archer_scan_jobs")
    op.drop_table("archer_scan_jobs")
    op.drop_index(
        op.f("ix_saved_archer_tournaments_user_id"), table_name="saved_archer_tournaments"
    )
    op.drop_index(
        op.f("ix_saved_archer_tournaments_tournament_id"),
        table_name="saved_archer_tournaments",
    )
    op.drop_table("saved_archer_tournaments")
    op.drop_index(op.f("ix_membership_numbers_user_id"), table_name="membership_numbers")
    op.drop_table("membership_numbers")
    op.drop_index(op.f("ix_archer_name_aliases_user_id"), table_name="archer_name_aliases")
    op.drop_table("archer_name_aliases")
    op.drop_column("users", "preferred_mode")
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
