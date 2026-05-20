from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.mode import MODE_ARCHER, MODE_CLUB, is_archer_mode, set_app_mode
from app.models import ArcherScanQueueItem, SavedArcherPractice, SavedArcherTournament
from app.services.archer_analytics import (
    analytics_has_data,
    analytics_to_chart_data,
    build_analytics,
)
from app.services.archer_filter import identity_from_user
from app.services.archer_metadata import update_round_metadata
from app.services.archer_practice import (
    PracticeValidationError,
    practice_round_count,
    rounds_from_form,
    validate_rounds,
)
from app.services.archer_queue import add_tournament_to_queue, queue_item_to_dict
from app.services.betweenends_client import BetweenendsAPIError, BetweenendsClient
from app.services.snapshot import load_snapshot
from app.services.summary import build_summary

archer_bp = Blueprint("archer", __name__, url_prefix="/my-results")


@archer_bp.route("/set-mode", methods=["POST"])
@login_required
def set_mode():
    mode = request.form.get("mode", MODE_CLUB)
    set_app_mode(mode)
    if mode == MODE_ARCHER:
        return redirect(url_for("archer.library"))
    return redirect(url_for("tournaments.index"))


def _require_archer_mode():
    if not is_archer_mode():
        set_app_mode(MODE_ARCHER)


def _get_saved(saved_id: int) -> SavedArcherTournament:
    return SavedArcherTournament.query.filter_by(
        id=saved_id, user_id=current_user.id
    ).first_or_404()


def _get_practice(practice_id: int) -> SavedArcherPractice:
    return SavedArcherPractice.query.filter_by(
        id=practice_id, user_id=current_user.id
    ).first_or_404()


def _sort_query(query, sort: str, direction: str):
    descending = direction == "desc"
    col = (
        SavedArcherTournament.start_date
        if sort == "date"
        else SavedArcherTournament.tournament_name
    )
    return query.order_by(col.desc() if descending else col.asc())


@archer_bp.route("/library")
@login_required
def library():
    _require_archer_mode()
    sort = request.args.get("sort", "date")
    if sort not in ("name", "date"):
        sort = "date"
    direction = request.args.get("dir", "desc")
    if direction not in ("asc", "desc"):
        direction = "desc"

    query = SavedArcherTournament.query.filter_by(user_id=current_user.id)
    saved = _sort_query(query, sort, direction).all()
    identity = identity_from_user(current_user)
    queue_items = (
        ArcherScanQueueItem.query.filter_by(user_id=current_user.id)
        .filter(ArcherScanQueueItem.status.in_(("pending", "processing")))
        .order_by(ArcherScanQueueItem.created_at.desc())
        .all()
    )

    practices = (
        SavedArcherPractice.query.filter_by(user_id=current_user.id)
        .order_by(SavedArcherPractice.practice_date.desc())
        .all()
    )
    edit_id = request.args.get("edit", type=int)
    edit_practice = None
    if edit_id:
        edit_practice = SavedArcherPractice.query.filter_by(
            id=edit_id, user_id=current_user.id
        ).first()

    return render_template(
        "archer/library.html",
        saved=saved,
        sort=sort,
        direction=direction,
        identity_configured=identity.is_configured(),
        queue_items=queue_items,
        practices=practices,
        edit_practice=edit_practice,
        practice_round_count=practice_round_count,
    )


@archer_bp.route("/library/<int:saved_id>")
@login_required
def library_view(saved_id: int):
    _require_archer_mode()
    saved = _get_saved(saved_id)
    tournament, events, _ = load_snapshot(saved.snapshot_json)
    summary = build_summary(events)
    return render_template(
        "archer/view.html",
        saved=saved,
        tournament=tournament,
        events=events,
        summary=summary,
        user_metadata=saved.user_metadata,
    )


@archer_bp.route("/library/<int:saved_id>/metadata", methods=["POST"])
@login_required
def library_metadata(saved_id: int):
    _require_archer_mode()
    saved = _get_saved(saved_id)
    event_id = request.form.get("event_id", type=int)
    round_index = request.form.get("round_index", type=int, default=0)
    distance = request.form.get("distance", "")
    conditions = request.form.get("conditions", "")
    notes = request.form.get("notes", "")
    if event_id is None:
        flash("Invalid event.", "error")
        return redirect(url_for("archer.library_view", saved_id=saved_id))

    saved.user_metadata = update_round_metadata(
        saved.user_metadata,
        event_id,
        round_index,
        distance,
        conditions,
        notes,
    )
    db.session.commit()
    flash("Round details saved.", "success")
    return redirect(url_for("archer.library_view", saved_id=saved_id))


@archer_bp.route("/library/<int:saved_id>/delete", methods=["POST"])
@login_required
def library_delete(saved_id: int):
    _require_archer_mode()
    saved = _get_saved(saved_id)
    db.session.delete(saved)
    db.session.commit()
    flash("Removed from your library.", "success")
    return redirect(url_for("archer.library"))


@archer_bp.route("/practice", methods=["POST"])
@login_required
def practice_create():
    _require_archer_mode()
    name = (request.form.get("name") or "").strip()
    practice_date = (request.form.get("practice_date") or "").strip()
    if not name or not practice_date:
        flash("Practice name and date are required.", "error")
        return redirect(url_for("archer.library") + "#archer-practice-section")

    try:
        rounds = validate_rounds(rounds_from_form(request.form))
    except PracticeValidationError as exc:
        flash(str(exc), "error")
        return redirect(url_for("archer.library") + "#archer-practice-section")

    practice = SavedArcherPractice(
        user_id=current_user.id,
        name=name,
        practice_date=practice_date,
        include_in_analytics=True,
        rounds_json=rounds,
    )
    db.session.add(practice)
    db.session.commit()
    flash("Practice session saved.", "success")
    return redirect(url_for("archer.library") + "#archer-practice-section")


@archer_bp.route("/practice/<int:practice_id>", methods=["POST"])
@login_required
def practice_update(practice_id: int):
    _require_archer_mode()
    practice = _get_practice(practice_id)
    name = (request.form.get("name") or "").strip()
    practice_date = (request.form.get("practice_date") or "").strip()
    if not name or not practice_date:
        flash("Practice name and date are required.", "error")
        return redirect(url_for("archer.library", edit=practice_id) + "#archer-practice-section")

    try:
        rounds = validate_rounds(rounds_from_form(request.form))
    except PracticeValidationError as exc:
        flash(str(exc), "error")
        return redirect(url_for("archer.library", edit=practice_id) + "#archer-practice-section")

    practice.name = name
    practice.practice_date = practice_date
    practice.rounds_json = rounds
    db.session.commit()
    flash("Practice session updated.", "success")
    return redirect(url_for("archer.library") + "#archer-practice-section")


@archer_bp.route("/practice/<int:practice_id>/delete", methods=["POST"])
@login_required
def practice_delete(practice_id: int):
    _require_archer_mode()
    practice = _get_practice(practice_id)
    db.session.delete(practice)
    db.session.commit()
    flash("Practice session removed.", "success")
    return redirect(url_for("archer.library") + "#archer-practice-section")


@archer_bp.route("/search")
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


@archer_bp.route("/queue", methods=["POST"])
@login_required
def queue_add():
    _require_archer_mode()
    identity = identity_from_user(current_user)
    if not identity.is_configured():
        return jsonify({"error": "Set your first and last name in Profile first."}), 400

    data = request.get_json(silent=True) or {}
    tournament_id = data.get("tournament_id") or request.form.get("tournament_id", type=int)
    tournament_name = (data.get("tournament_name") or request.form.get("tournament_name") or "").strip()
    if not tournament_id:
        return jsonify({"error": "Select a tournament first."}), 400
    if not tournament_name:
        tournament_name = f"Tournament {tournament_id}"

    try:
        item = add_tournament_to_queue(
            current_user.id, int(tournament_id), tournament_name
        )
        return jsonify(queue_item_to_dict(item))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@archer_bp.route("/queue")
@login_required
def queue_list():
    items = (
        ArcherScanQueueItem.query.filter_by(user_id=current_user.id)
        .order_by(ArcherScanQueueItem.created_at.desc())
        .limit(50)
        .all()
    )
    return jsonify([queue_item_to_dict(i) for i in items])


@archer_bp.route("/analytics")
@login_required
def analytics():
    _require_archer_mode()
    include_practice = request.args.get("include_practice", "1") != "0"
    saved = (
        SavedArcherTournament.query.filter_by(user_id=current_user.id)
        .order_by(SavedArcherTournament.start_date.asc())
        .all()
    )
    practices = (
        SavedArcherPractice.query.filter_by(user_id=current_user.id)
        .order_by(SavedArcherPractice.practice_date.asc())
        .all()
        if include_practice
        else []
    )
    if not saved and not practices:
        return render_template(
            "archer/analytics.html",
            chart_data=None,
            has_data=False,
            include_practice=include_practice,
        )

    analytics_result = build_analytics(
        saved, practices=practices, include_practice=include_practice
    )
    chart_data = analytics_to_chart_data(analytics_result)
    return render_template(
        "archer/analytics.html",
        chart_data=chart_data,
        has_data=analytics_has_data(analytics_result),
        include_practice=include_practice,
        has_scores=bool(analytics_result.scores_by_distance or analytics_result.normalized_scores),
        has_consistency=bool(analytics_result.consistency),
        has_elimination=bool(analytics_result.elimination),
    )
