"""Per-tournament archer scan queue backed by Redis RQ."""

from datetime import datetime

from flask import current_app

from app.extensions import db
from app.models import ArcherScanQueueItem, SavedArcherTournament
from app.services.archer_filter import identity_from_user
from app.services.betweenends_client import BetweenendsAPIError, BetweenendsClient
from app.services.snapshot import build_snapshot
from app.services.tournament_loader import fetch_archer_tournament_results


def get_redis_connection():
    from redis import Redis

    return Redis.from_url(current_app.config["REDIS_URL"])


def get_scan_queue():
    from rq import Queue

    return Queue(
        current_app.config.get("ARCHER_SCAN_QUEUE_NAME", "archer-scans"),
        connection=get_redis_connection(),
    )


def enqueue_queue_item(item_id: int) -> None:
    if current_app.config.get("TESTING"):
        process_queue_item(item_id)
        return
    queue = get_scan_queue()
    queue.enqueue(
        process_queue_item,
        item_id,
        job_timeout=current_app.config.get("ARCHER_SCAN_JOB_TIMEOUT", 600),
        result_ttl=300,
    )


def add_tournament_to_queue(
    user_id: int,
    tournament_id: int,
    tournament_name: str,
) -> ArcherScanQueueItem:
    existing = ArcherScanQueueItem.query.filter_by(
        user_id=user_id,
        tournament_id=tournament_id,
        status="pending",
    ).first()
    if existing:
        return existing

    processing = ArcherScanQueueItem.query.filter_by(
        user_id=user_id,
        tournament_id=tournament_id,
        status="processing",
    ).first()
    if processing:
        return processing

    item = ArcherScanQueueItem(
        user_id=user_id,
        tournament_id=tournament_id,
        tournament_name=tournament_name,
        status="pending",
    )
    db.session.add(item)
    db.session.commit()
    enqueue_queue_item(item.id)
    return item


def process_queue_item(item_id: int) -> None:
    from flask import has_app_context

    if has_app_context():
        _run_queue_item(item_id)
        return

    from app import create_app

    app = create_app()
    with app.app_context():
        _run_queue_item(item_id)


def _run_queue_item(item_id: int) -> None:
    from app.models import User

    item = db.session.get(ArcherScanQueueItem, item_id)
    if not item or item.status not in ("pending", "processing"):
        return

    user = db.session.get(User, item.user_id)
    if not user:
        item.status = "failed"
        item.error_message = "User not found."
        item.completed_at = datetime.utcnow()
        db.session.commit()
        return

    identity = identity_from_user(user)
    if not identity.is_configured():
        item.status = "failed"
        item.error_message = "Set first and last name in Profile."
        item.completed_at = datetime.utcnow()
        db.session.commit()
        return

    item.status = "processing"
    item.started_at = datetime.utcnow()
    db.session.commit()

    try:
        client = BetweenendsClient()
        tournament, events, summary = fetch_archer_tournament_results(
            client, item.tournament_id, identity
        )
        if not events:
            item.status = "not_found"
            item.error_message = "No results found for you in this tournament."
            item.completed_at = datetime.utcnow()
            db.session.commit()
            return

        snapshot = build_snapshot(item.tournament_id, tournament, events, summary)
        match_reason = None
        for event in events:
            for div in event.divisions:
                for archer in div.archers:
                    if archer.match_reason:
                        match_reason = archer.match_reason
                        break

        saved = SavedArcherTournament.query.filter_by(
            user_id=item.user_id,
            tournament_id=item.tournament_id,
        ).first()

        if saved:
            saved.tournament_name = tournament.get("tournament_name", item.tournament_name)
            saved.location = tournament.get("location")
            saved.start_date = tournament.get("start_date")
            saved.end_date = tournament.get("end_date")
            saved.match_reason = match_reason
            saved.snapshot_json = snapshot
            saved.saved_at = datetime.utcnow()
        else:
            saved = SavedArcherTournament(
                user_id=item.user_id,
                tournament_id=item.tournament_id,
                tournament_name=tournament.get("tournament_name", item.tournament_name),
                location=tournament.get("location"),
                start_date=tournament.get("start_date"),
                end_date=tournament.get("end_date"),
                match_reason=match_reason,
                snapshot_json=snapshot,
                user_metadata={"events": []},
            )
            db.session.add(saved)

        item.status = "completed"
        item.completed_at = datetime.utcnow()
        db.session.commit()
    except BetweenendsAPIError as exc:
        item.status = "failed"
        item.error_message = str(exc)
        item.completed_at = datetime.utcnow()
        db.session.commit()
    except Exception as exc:
        item.status = "failed"
        item.error_message = str(exc)
        item.completed_at = datetime.utcnow()
        db.session.commit()
        raise


def queue_item_to_dict(item: ArcherScanQueueItem) -> dict:
    return {
        "id": item.id,
        "tournament_id": item.tournament_id,
        "tournament_name": item.tournament_name,
        "status": item.status,
        "error_message": item.error_message,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "completed_at": item.completed_at.isoformat() if item.completed_at else None,
    }
