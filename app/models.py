from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(128), nullable=True)
    last_name = db.Column(db.String(128), nullable=True)
    preferred_mode = db.Column(db.String(20), default="club", nullable=False)
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


class ArcherNameAlias(db.Model):
    __tablename__ = "archer_name_aliases"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    alias = db.Column(db.String(255), nullable=False)

    user = db.relationship(
        "User", backref=db.backref("archer_name_aliases", cascade="all, delete-orphan")
    )


class MembershipNumber(db.Model):
    __tablename__ = "membership_numbers"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    organization = db.Column(db.String(128), nullable=False)
    number = db.Column(db.String(64), nullable=False)

    user = db.relationship(
        "User", backref=db.backref("membership_numbers", cascade="all, delete-orphan")
    )


class SavedArcherTournament(db.Model):
    __tablename__ = "saved_archer_tournaments"
    __table_args__ = (
        db.UniqueConstraint("user_id", "tournament_id", name="uq_saved_archer_tournament_user"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    tournament_id = db.Column(db.Integer, nullable=False, index=True)
    tournament_name = db.Column(db.String(512), nullable=False)
    location = db.Column(db.String(512), nullable=True)
    start_date = db.Column(db.String(32), nullable=True)
    end_date = db.Column(db.String(32), nullable=True)
    match_reason = db.Column(db.String(32), nullable=True)
    snapshot_json = db.Column(db.JSON, nullable=False)
    user_metadata = db.Column(db.JSON, nullable=True)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship(
        "User",
        backref=db.backref("saved_archer_tournaments", cascade="all, delete-orphan"),
    )


class ArcherScanQueueItem(db.Model):
    __tablename__ = "archer_scan_queue_items"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    tournament_id = db.Column(db.Integer, nullable=False, index=True)
    tournament_name = db.Column(db.String(512), nullable=False)
    status = db.Column(db.String(20), default="pending", nullable=False)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship(
        "User",
        backref=db.backref("archer_scan_queue_items", cascade="all, delete-orphan"),
    )


class ArcherScanJob(db.Model):
    __tablename__ = "archer_scan_jobs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    status = db.Column(db.String(20), default="pending", nullable=False)
    scope = db.Column(db.String(20), default="recent", nullable=False)
    progress_current = db.Column(db.Integer, default=0, nullable=False)
    progress_total = db.Column(db.Integer, default=0, nullable=False)
    tournaments_added = db.Column(db.Integer, default=0, nullable=False)
    tournaments_skipped = db.Column(db.Integer, default=0, nullable=False)
    error_message = db.Column(db.Text, nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship(
        "User", backref=db.backref("archer_scan_jobs", cascade="all, delete-orphan")
    )
