from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.models import Club
from app.services.betweenends_client import BetweenendsAPIError, BetweenendsClient
from app.services.tournament_loader import club_alias_rules, fetch_tournament_results
from app.services.pdf_export import pdf_filename, pdf_response

tournaments_bp = Blueprint("tournaments", __name__)


@tournaments_bp.route("/")
def index():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    clubs = Club.query.filter_by(user_id=current_user.id).order_by(Club.name).all()
    default_club = next((c for c in clubs if c.is_default), clubs[0] if clubs else None)
    return render_template("tournaments/index.html", clubs=clubs, default_club=default_club)


@tournaments_bp.route("/search")
@login_required
def search():
    query = request.args.get("q", "").strip()
    if len(query) < 2:
        return jsonify([])
    try:
        client = BetweenendsClient()
        results = client.search_tournaments(query, limit=20)
        return jsonify(
            [
                {
                    "id": t.tournament_id,
                    "name": t.tournament_name,
                    "location": t.location,
                    "start_date": t.start_date,
                    "end_date": t.end_date,
                }
                for t in results
            ]
        )
    except BetweenendsAPIError as exc:
        return jsonify({"error": str(exc)}), 502


def _resolve_club():
    clubs = Club.query.filter_by(user_id=current_user.id).order_by(Club.name).all()
    if not clubs:
        return None, None, clubs

    club_id = request.values.get("club_id", type=int)
    if not club_id:
        default = next((c for c in clubs if c.is_default), clubs[0])
        club_id = default.id

    club = Club.query.filter_by(id=club_id, user_id=current_user.id).first_or_404()
    return club, club_id, clubs


@tournaments_bp.route("/<int:tournament_id>/results", methods=["GET", "POST"])
@login_required
def results(tournament_id: int):
    club, club_id, clubs = _resolve_club()
    if not club:
        flash("Add at least one club in your profile before viewing results.", "error")
        return redirect(url_for("profile.index"))

    aliases = club_alias_rules(club)

    try:
        client = BetweenendsClient()
        tournament, parsed_events, summary = fetch_tournament_results(
            client, tournament_id, aliases
        )
    except BetweenendsAPIError as exc:
        flash(f"Could not load tournament: {exc}", "error")
        return redirect(url_for("tournaments.index"))

    return render_template(
        "tournaments/results.html",
        tournament=tournament,
        tournament_id=tournament_id,
        club=club,
        clubs=clubs,
        events=parsed_events,
        summary=summary,
    )


@tournaments_bp.route("/<int:tournament_id>/results/pdf")
@login_required
def results_pdf(tournament_id: int):
    club, club_id, clubs = _resolve_club()
    if not club:
        flash("Add at least one club in your profile before exporting results.", "error")
        return redirect(url_for("profile.index"))

    aliases = club_alias_rules(club)

    try:
        client = BetweenendsClient()
        tournament, parsed_events, summary = fetch_tournament_results(
            client, tournament_id, aliases
        )
    except BetweenendsAPIError as exc:
        flash(f"Could not load tournament: {exc}", "error")
        return redirect(url_for("tournaments.index"))

    name = tournament.get("tournament_name", "Tournament")
    return pdf_response(
        tournament=tournament,
        club_name=club.name,
        events=parsed_events,
        summary=summary,
        filename=pdf_filename(name),
    )
