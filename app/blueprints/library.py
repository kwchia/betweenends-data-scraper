from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Club, SavedTournament
from app.services.betweenends_client import BetweenendsAPIError, BetweenendsClient
from app.services.pdf_export import pdf_filename, pdf_response
from app.services.snapshot import build_snapshot, load_snapshot
from app.services.tournament_loader import club_alias_rules, fetch_tournament_results

library_bp = Blueprint("library", __name__, url_prefix="/library")


def _get_saved(saved_id: int) -> SavedTournament:
    return SavedTournament.query.filter_by(id=saved_id, user_id=current_user.id).first_or_404()


def _sort_query(query, sort: str, direction: str):
    descending = direction == "desc"
    if sort == "date":
        col = SavedTournament.start_date
    else:
        col = SavedTournament.tournament_name
    return query.order_by(col.desc() if descending else col.asc())


@library_bp.route("/")
@login_required
def index():
    sort = request.args.get("sort", "date")
    if sort not in ("name", "date"):
        sort = "date"
    direction = request.args.get("dir", "desc")
    if direction not in ("asc", "desc"):
        direction = "desc"

    query = SavedTournament.query.filter_by(user_id=current_user.id)
    saved = _sort_query(query, sort, direction).all()

    return render_template(
        "library/index.html",
        saved=saved,
        sort=sort,
        direction=direction,
    )


@library_bp.route("/save", methods=["POST"])
@login_required
def save():
    tournament_id = request.form.get("tournament_id", type=int)
    club_id = request.form.get("club_id", type=int)
    if not tournament_id or not club_id:
        flash("Could not save: missing tournament or club.", "error")
        return redirect(request.referrer or url_for("tournaments.index"))

    club = Club.query.filter_by(id=club_id, user_id=current_user.id).first_or_404()
    aliases = club_alias_rules(club)

    try:
        client = BetweenendsClient()
        tournament, events, summary = fetch_tournament_results(
            client, tournament_id, aliases
        )
    except BetweenendsAPIError as exc:
        flash(f"Could not save results: {exc}", "error")
        return redirect(url_for("tournaments.results", tournament_id=tournament_id, club_id=club_id))

    snapshot = build_snapshot(tournament_id, tournament, events, summary)
    existing = SavedTournament.query.filter_by(
        user_id=current_user.id,
        tournament_id=tournament_id,
        club_id=club_id,
    ).first()

    if existing:
        existing.tournament_name = tournament.get("tournament_name", "Tournament")
        existing.location = tournament.get("location")
        existing.start_date = tournament.get("start_date")
        existing.end_date = tournament.get("end_date")
        existing.club_name = club.name
        existing.snapshot_json = snapshot
        existing.saved_at = datetime.utcnow()
        message = "Library entry updated."
    else:
        entry = SavedTournament(
            user_id=current_user.id,
            tournament_id=tournament_id,
            club_id=club_id,
            tournament_name=tournament.get("tournament_name", "Tournament"),
            location=tournament.get("location"),
            start_date=tournament.get("start_date"),
            end_date=tournament.get("end_date"),
            club_name=club.name,
            snapshot_json=snapshot,
        )
        db.session.add(entry)
        message = "Saved to your library."

    db.session.commit()
    flash(message, "success")
    return redirect(url_for("library.index"))


@library_bp.route("/<int:saved_id>")
@login_required
def view(saved_id: int):
    saved = _get_saved(saved_id)
    tournament, events, summary = load_snapshot(saved.snapshot_json)
    return render_template(
        "library/view.html",
        saved=saved,
        tournament=tournament,
        club_name=saved.club_name,
        events=events,
        summary=summary,
    )


@library_bp.route("/<int:saved_id>/delete", methods=["POST"])
@login_required
def delete(saved_id: int):
    saved = _get_saved(saved_id)
    db.session.delete(saved)
    db.session.commit()
    flash("Removed from library.", "success")
    return redirect(url_for("library.index"))


@library_bp.route("/<int:saved_id>/pdf")
@login_required
def pdf(saved_id: int):
    saved = _get_saved(saved_id)
    tournament, events, summary = load_snapshot(saved.snapshot_json)
    return pdf_response(
        tournament=tournament,
        club_name=saved.club_name,
        events=events,
        summary=summary,
        filename=pdf_filename(saved.tournament_name),
    )


