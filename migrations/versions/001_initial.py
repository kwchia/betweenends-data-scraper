"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-16

"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("default_club_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "clubs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_clubs_user_id"), "clubs", ["user_id"], unique=False)

    op.create_table(
        "club_aliases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("club_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(length=255), nullable=False),
        sa.Column("match_mode", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["clubs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_club_aliases_club_id"), "club_aliases", ["club_id"], unique=False)

    op.create_foreign_key("fk_users_default_club", "users", "clubs", ["default_club_id"], ["id"])

    op.create_table(
        "tournament_cache",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("tournament_name", sa.String(length=512), nullable=False),
        sa.Column("location", sa.String(length=512), nullable=True),
        sa.Column("start_date", sa.String(length=32), nullable=True),
        sa.Column("end_date", sa.String(length=32), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tournament_cache_tournament_id"),
        "tournament_cache",
        ["tournament_id"],
        unique=True,
    )

    op.create_table(
        "tournament_list_meta",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("tournament_list_meta")
    op.drop_index(op.f("ix_tournament_cache_tournament_id"), table_name="tournament_cache")
    op.drop_table("tournament_cache")
    op.drop_constraint("fk_users_default_club", "users", type_="foreignkey")
    op.drop_index(op.f("ix_club_aliases_club_id"), table_name="club_aliases")
    op.drop_table("club_aliases")
    op.drop_index(op.f("ix_clubs_user_id"), table_name="clubs")
    op.drop_table("clubs")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
