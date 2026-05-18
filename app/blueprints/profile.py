from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Club, ClubAlias

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")


@profile_bp.route("/")
@login_required
def index():
    clubs = Club.query.filter_by(user_id=current_user.id).order_by(Club.name).all()
    return render_template("profile/index.html", clubs=clubs)


@profile_bp.route("/clubs/new", methods=["GET", "POST"])
@login_required
def new_club():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Club name is required.", "error")
        else:
            club = Club(user_id=current_user.id, name=name)
            is_first = Club.query.filter_by(user_id=current_user.id).count() == 0
            if is_first or request.form.get("is_default"):
                club.is_default = True
                _clear_default_clubs(current_user.id)
            db.session.add(club)
            db.session.flush()

            alias_text = request.form.get("aliases", "").strip()
            for line in alias_text.splitlines():
                line = line.strip()
                if line:
                    db.session.add(ClubAlias(club_id=club.id, alias=line, match_mode="exact"))

            if club.is_default:
                current_user.default_club_id = club.id

            db.session.commit()
            flash(f"Club '{name}' created.", "success")
            return redirect(url_for("profile.edit_club", club_id=club.id))

    return render_template("profile/club_form.html", club=None, aliases=[])


@profile_bp.route("/clubs/<int:club_id>", methods=["GET", "POST"])
@login_required
def edit_club(club_id):
    club = _get_user_club(club_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Club name is required.", "error")
        else:
            club.name = name
            if request.form.get("is_default"):
                _clear_default_clubs(current_user.id)
                club.is_default = True
                current_user.default_club_id = club.id
            db.session.commit()
            flash("Club updated.", "success")
            return redirect(url_for("profile.edit_club", club_id=club.id))

    return render_template("profile/club_form.html", club=club, aliases=club.aliases)


@profile_bp.route("/clubs/<int:club_id>/aliases", methods=["POST"])
@login_required
def add_alias(club_id):
    club = _get_user_club(club_id)
    alias = request.form.get("alias", "").strip()
    match_mode = request.form.get("match_mode", "exact")
    if not alias:
        flash("Alias cannot be empty.", "error")
    elif match_mode not in ("exact", "contains"):
        flash("Invalid match mode.", "error")
    else:
        db.session.add(ClubAlias(club_id=club.id, alias=alias, match_mode=match_mode))
        db.session.commit()
        flash("Alias added.", "success")
    return redirect(url_for("profile.edit_club", club_id=club.id))


@profile_bp.route("/clubs/<int:club_id>/aliases/<int:alias_id>/delete", methods=["POST"])
@login_required
def delete_alias(club_id, alias_id):
    club = _get_user_club(club_id)
    alias = ClubAlias.query.filter_by(id=alias_id, club_id=club.id).first_or_404()
    db.session.delete(alias)
    db.session.commit()
    flash("Alias removed.", "info")
    return redirect(url_for("profile.edit_club", club_id=club.id))


@profile_bp.route("/clubs/<int:club_id>/delete", methods=["POST"])
@login_required
def delete_club(club_id):
    club = _get_user_club(club_id)
    was_default = club.is_default
    db.session.delete(club)
    db.session.commit()

    if was_default:
        remaining = Club.query.filter_by(user_id=current_user.id).first()
        if remaining:
            remaining.is_default = True
            current_user.default_club_id = remaining.id
            db.session.commit()
        else:
            current_user.default_club_id = None
            db.session.commit()

    flash("Club deleted.", "info")
    return redirect(url_for("profile.index"))


def _get_user_club(club_id: int) -> Club:
    return Club.query.filter_by(id=club_id, user_id=current_user.id).first_or_404()


def _clear_default_clubs(user_id: int) -> None:
    Club.query.filter_by(user_id=user_id).update({"is_default": False})
