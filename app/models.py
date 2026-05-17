from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    default_club_id = db.Column(
        db.Integer, db.ForeignKey("clubs.id", use_alter=True), nullable=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    clubs = db.relationship(
        "Club",
        back_populates="user",
        foreign_keys="Club.user_id",
        cascade="all, delete-orphan",
    )
    default_club = db.relationship("Club", foreign_keys=[default_club_id], post_update=True)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Club(db.Model):
    __tablename__ = "clubs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="clubs", foreign_keys=[user_id])
    aliases = db.relationship(
        "ClubAlias", back_populates="club", cascade="all, delete-orphan"
    )


class ClubAlias(db.Model):
    __tablename__ = "club_aliases"

    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey("clubs.id"), nullable=False, index=True)
    alias = db.Column(db.String(255), nullable=False)
    match_mode = db.Column(db.String(20), default="contains", nullable=False)

    club = db.relationship("Club", back_populates="aliases")


class TournamentCache(db.Model):
    __tablename__ = "tournament_cache"

    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, unique=True, nullable=False, index=True)
    tournament_name = db.Column(db.String(512), nullable=False)
    location = db.Column(db.String(512), nullable=True)
    start_date = db.Column(db.String(32), nullable=True)
    end_date = db.Column(db.String(32), nullable=True)
    updated_at = db.Column(db.DateTime, nullable=True)
    fetched_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class TournamentListMeta(db.Model):
    """Tracks when the full tournament list was last synced."""

    __tablename__ = "tournament_list_meta"

    id = db.Column(db.Integer, primary_key=True)
    fetched_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class SavedTournament(db.Model):
    __tablename__ = "saved_tournaments"
    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "tournament_id", "club_id", name="uq_saved_tournament_user_club"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    tournament_id = db.Column(db.Integer, nullable=False, index=True)
    club_id = db.Column(db.Integer, db.ForeignKey("clubs.id"), nullable=True)
    tournament_name = db.Column(db.String(512), nullable=False)
    location = db.Column(db.String(512), nullable=True)
    start_date = db.Column(db.String(32), nullable=True)
    end_date = db.Column(db.String(32), nullable=True)
    club_name = db.Column(db.String(255), nullable=False)
    snapshot_json = db.Column(db.JSON, nullable=False)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", backref=db.backref("saved_tournaments", cascade="all, delete-orphan"))
    club = db.relationship("Club")
