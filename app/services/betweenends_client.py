from datetime import datetime, timedelta
from typing import Any, Optional

import httpx
from flask import current_app
from sqlalchemy import or_

from app.extensions import db
from app.models import TournamentCache, TournamentListMeta


class BetweenendsAPIError(Exception):
    pass


class BetweenendsClient:
    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0):
        self.base_url = (base_url or current_app.config["BETWEENENDS_API_BASE"]).rstrip("/")
        self.timeout = timeout

    def _get(self, path: str) -> Any:
        url = f"{self.base_url}{path}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            raise BetweenendsAPIError(f"Failed to fetch {url}: {exc}") from exc

    def list_tournaments_raw(self) -> list[dict]:
        return self._get("/tournaments")

    def get_tournament(self, tournament_id: int) -> dict:
        return self._get(f"/tournaments/{tournament_id}")

    def get_event(self, event_id: int) -> dict:
        return self._get(f"/events/{event_id}")

    def get_event_scores(self, event_id: int) -> dict:
        return self._get(f"/events/{event_id}/scores")

    def sync_tournament_cache(self, force: bool = False) -> int:
        ttl_hours = current_app.config.get("TOURNAMENT_CACHE_TTL_HOURS", 24)
        meta = TournamentListMeta.query.order_by(TournamentListMeta.fetched_at.desc()).first()
        stale = (
            force
            or meta is None
            or meta.fetched_at < datetime.utcnow() - timedelta(hours=ttl_hours)
        )
        if not stale and TournamentCache.query.count() > 0:
            return TournamentCache.query.count()

        tournaments = self.list_tournaments_raw()
        TournamentCache.query.delete()
        for t in tournaments:
            db.session.add(
                TournamentCache(
                    tournament_id=t["id"],
                    tournament_name=t.get("tournament_name", ""),
                    location=t.get("location"),
                    start_date=t.get("start_date"),
                    end_date=t.get("end_date"),
                    updated_at=_parse_dt(t.get("updated_at")),
                )
            )
        db.session.add(TournamentListMeta(fetched_at=datetime.utcnow()))
        db.session.commit()
        return len(tournaments)

    def search_tournaments(self, query: str, limit: int = 25) -> list[TournamentCache]:
        self.sync_tournament_cache()
        q = f"%{query.strip().lower()}%"
        return (
            TournamentCache.query.filter(
                or_(
                    db.func.lower(TournamentCache.tournament_name).like(q),
                    db.func.lower(TournamentCache.location).like(q),
                )
            )
            .order_by(TournamentCache.start_date.desc())
            .limit(limit)
            .all()
        )


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None
