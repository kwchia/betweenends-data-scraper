from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import ArcherNameAlias, Club, ClubAlias, MembershipNumber

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")


@profile_bp.route("/")
@login_required
def index():
    clubs = Club.query.filter_by(user_id=current_user.id).order_by(Club.name).all()
    name_aliases = ArcherNameAlias.query.filter_by(user_id=current_user.id).all()
    memberships = MembershipNumber.query.filter_by(user_id=current_user.id).all()
    return render_template(
        "profile/index.html",
        clubs=clubs,
        name_aliases=name_aliases,
        memberships=memberships,
    )


@profile_bp.route("/archer-identity", methods=["POST"])
@login_required
def save_archer_identity():
    first = request.form.get("first_name", "").strip()
    last = request.form.get("last_name", "").strip()
    if not first or not last:
        flash("First and last name are required.", "error")
    else:
        current_user.first_name = first
        current_user.last_name = last
        db.session.commit()
        flash("Archer identity saved.", "success")
    return redirect(url_for("profile.index"))


@profile_bp.route("/name-aliases", methods=["POST"])
@login_required
def add_name_alias():
    alias = request.form.get("alias", "").strip()
    if not alias:
        flash("Alias cannot be empty.", "error")
    else:
        db.session.add(ArcherNameAlias(user_id=current_user.id, alias=alias))
        db.session.commit()
        flash("Name alias added.", "success")
    return redirect(url_for("profile.index"))


@profile_bp.route("/name-aliases/<int:alias_id>/delete", methods=["POST"])
@login_required
def delete_name_alias(alias_id):
    alias = ArcherNameAlias.query.filter_by(id=alias_id, user_id=current_user.id).first_or_404()
    db.session.delete(alias)
    db.session.commit()
    flash("Alias removed.", "info")
    return redirect(url_for("profile.index"))


@profile_bp.route("/memberships", methods=["POST"])
@login_required
def add_membership():
    org = request.form.get("organization", "").strip()
    number = request.form.get("number", "").strip()
    if not org or not number:
        flash("Organization and number are required.", "error")
    else:
        db.session.add(
            MembershipNumber(user_id=current_user.id, organization=org, number=number)
        )
        db.session.commit()
        flash("Membership added.", "success")
    return redirect(url_for("profile.index"))


@profile_bp.route("/memberships/<int:membership_id>/delete", methods=["POST"])
@login_required
def delete_membership(membership_id):
    row = MembershipNumber.query.filter_by(
        id=membership_id, user_id=current_user.id
    ).first_or_404()
    db.session.delete(row)
    db.session.commit()
    flash("Membership removed.", "info")
    return redirect(url_for("profile.index"))


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
                    db.session.add(ClubAlias(club_id=club.id, alias=line, match_mode="contains"))

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
    match_mode = request.form.get("match_mode", "contains")
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
