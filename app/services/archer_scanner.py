"""Background scan of Betweenends tournaments for an archer's results."""

import threading
from datetime import datetime, timedelta
from typing import Optional

from flask import current_app

from app.extensions import db
from app.models import ArcherScanJob, SavedArcherTournament, TournamentCache
from app.services.archer_filter import ArcherIdentity, identity_from_user
from app.services.betweenends_client import BetweenendsAPIError, BetweenendsClient
from app.services.snapshot import build_snapshot
from app.services.tournament_loader import fetch_archer_tournament_results


def _parse_tournament_date(start_date: Optional[str]) -> Optional[datetime]:
    if not start_date:
        return None
    try:
        return datetime.strptime(start_date[:10], "%Y-%m-%d")
    except ValueError:
        return None


def _recent_cutoff(scope: str) -> Optional[datetime]:
    if scope == "full_history":
        return None
    years = current_app.config.get("ARCHER_SCAN_RECENT_YEARS", 3)
    return datetime.utcnow() - timedelta(days=years * 365)


def _candidate_tournaments(user_id: int, scope: str) -> list[TournamentCache]:
    client = BetweenendsClient()
    client.sync_tournament_cache()
    cutoff = _recent_cutoff(scope)
    existing_ids = {
        row.tournament_id
        for row in SavedArcherTournament.query.filter_by(user_id=user_id).all()
    }
    query = TournamentCache.query.order_by(TournamentCache.start_date.desc())
    candidates = []
    for row in query.all():
        if row.tournament_id in existing_ids:
            continue
        if cutoff:
            dt = _parse_tournament_date(row.start_date)
            if dt and dt < cutoff:
                continue
        candidates.append(row)
    return candidates


def run_scan_job(job_id: int, app) -> None:
    with app.app_context():
        from app.models import User

        job = db.session.get(ArcherScanJob, job_id)
        if not job:
            return
        user = db.session.get(User, job.user_id)
        if not user:
            return
        identity = identity_from_user(user)
        if not identity.is_configured():
            job.status = "failed"
            job.error_message = "Set your first and last name in Profile before scanning."
            job.completed_at = datetime.utcnow()
            db.session.commit()
            return

        job.status = "running"
        job.started_at = datetime.utcnow()
        db.session.commit()

        batch_every = current_app.config.get("ARCHER_SCAN_BATCH_COMMIT_EVERY", 10)
        try:
            candidates = _candidate_tournaments(job.user_id, job.scope)
            job.progress_total = len(candidates)
            db.session.commit()

            client = BetweenendsClient()
            for i, cached in enumerate(candidates):
                job = db.session.get(ArcherScanJob, job_id)
                if not job or job.status == "failed":
                    return
                try:
                    tournament, events, summary = fetch_archer_tournament_results(
                        client, cached.tournament_id, identity
                    )
                    if events:
                        snapshot = build_snapshot(
                            cached.tournament_id, tournament, events, summary
                        )
                        match_reason = None
                        for event in events:
                            for div in event.divisions:
                                for archer in div.archers:
                                    if archer.match_reason:
                                        match_reason = archer.match_reason
                                        break
                        entry = SavedArcherTournament(
                            user_id=job.user_id,
                            tournament_id=cached.tournament_id,
                            tournament_name=tournament.get(
                                "tournament_name", cached.tournament_name
                            ),
                            location=tournament.get("location") or cached.location,
                            start_date=tournament.get("start_date") or cached.start_date,
                            end_date=tournament.get("end_date") or cached.end_date,
                            match_reason=match_reason,
                            snapshot_json=snapshot,
                            user_metadata={"events": []},
                        )
                        db.session.add(entry)
                        job.tournaments_added += 1
                    else:
                        job.tournaments_skipped += 1
                except BetweenendsAPIError:
                    job.tournaments_skipped += 1

                job.progress_current = i + 1
                if (i + 1) % batch_every == 0:
                    db.session.commit()

            job = db.session.get(ArcherScanJob, job_id)
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            db.session.commit()
        except Exception as exc:
            job = db.session.get(ArcherScanJob, job_id)
            if job:
                job.status = "failed"
                job.error_message = str(exc)
                job.completed_at = datetime.utcnow()
                db.session.commit()


def start_scan_job(user_id: int, scope: str) -> ArcherScanJob:
    running = ArcherScanJob.query.filter_by(user_id=user_id, status="running").first()
    if running:
        return running

    job = ArcherScanJob(user_id=user_id, status="pending", scope=scope)
    db.session.add(job)
    db.session.commit()

    app = current_app._get_current_object()
    thread = threading.Thread(target=run_scan_job, args=(job.id, app), daemon=True)
    thread.start()
    return job


def job_to_dict(job: ArcherScanJob) -> dict:
    return {
        "job_id": job.id,
        "status": job.status,
        "scope": job.scope,
        "progress_current": job.progress_current,
        "progress_total": job.progress_total,
        "tournaments_added": job.tournaments_added,
        "tournaments_skipped": job.tournaments_skipped,
        "error_message": job.error_message,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }
