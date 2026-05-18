"""Serialize and deserialize tournament result snapshots for the library."""

from dataclasses import asdict

from app.services.event_parsers import (
    ArcherResult,
    DivisionResult,
    EndScore,
    EventResult,
    MatchResult,
    MatchSide,
)
from app.services.summary import (
    Highlight,
    MedalCounts,
    MedalWinner,
    RosterEntry,
    TeamRosterEntry,
    TournamentSummary,
    build_individual_roster,
    build_team_roster,
    count_unique_archers,
)


def build_snapshot(
    tournament_id: int,
    tournament: dict,
    events: list[EventResult],
    summary: TournamentSummary,
) -> dict:
    return {
        "tournament_id": tournament_id,
        "tournament": {
            "tournament_name": tournament.get("tournament_name", ""),
            "location": tournament.get("location"),
            "start_date": tournament.get("start_date"),
            "end_date": tournament.get("end_date"),
        },
        "events": [asdict(e) for e in events],
        "summary": asdict(summary),
    }


def load_snapshot(data: dict) -> tuple[dict, list[EventResult], TournamentSummary]:
    tournament = data.get("tournament") or {}
    events = [_event_from_dict(e) for e in data.get("events") or []]
    summary = _summary_from_dict(data.get("summary") or {})
    summary.total_archers = count_unique_archers(events)
    summary.individual_roster = build_individual_roster(events)
    summary.team_roster = build_team_roster(events)
    return tournament, events, summary


def _event_from_dict(data: dict) -> EventResult:
    return EventResult(
        event_id=data["event_id"],
        event_name=data["event_name"],
        event_type=data["event_type"],
        display_order=data.get("display_order", 0),
        divisions=[_division_from_dict(d) for d in data.get("divisions") or []],
    )


def _division_from_dict(data: dict) -> DivisionResult:
    return DivisionResult(
        name=data["name"],
        archers=[_archer_from_dict(a) for a in data.get("archers") or []],
        rounds=data.get("rounds") or [],
    )


def _archer_from_dict(data: dict) -> ArcherResult:
    return ArcherResult(
        name=data["name"],
        club=data["club"],
        rank=data.get("rank"),
        total_score=data.get("total_score"),
        round_scores=data.get("round_scores") or [],
        matches=[_match_from_dict(m) for m in data.get("matches") or []],
        points=data.get("points"),
    )


def _match_from_dict(data: dict) -> MatchResult:
    return MatchResult(
        round_name=data["round_name"],
        round_index=data.get("round_index", 0),
        sides=[_match_side_from_dict(s) for s in data.get("sides") or []],
    )


def _match_side_from_dict(data: dict) -> MatchSide:
    return MatchSide(
        name=data["name"],
        club=data["club"],
        rank=data.get("rank"),
        target=data.get("target", ""),
        end_scores=[EndScore(**e) for e in data.get("end_scores") or []],
        total=data.get("total", 0),
        won=data.get("won", False),
    )


def _medal_winners_from_dict(data: dict, key: str) -> list[MedalWinner]:
    return [MedalWinner(**w) for w in data.get(key) or []]


def _medal_winners_from_highlights(highlights: list[dict]) -> list[MedalWinner]:
    winners: list[MedalWinner] = []
    for h in highlights:
        if h.get("kind") != "medal":
            continue
        title = h.get("title") or ""
        if not title.startswith("Gold — "):
            continue
        detail = h.get("detail") or ""
        if detail.endswith(")"):
            detail = detail.rsplit(" (", 1)[0]
        winners.append(
            MedalWinner(
                archer_name=title[len("Gold — ") :],
                event_name=h.get("event_name") or "",
                detail=detail,
            )
        )
    return winners


def _finishes_by_event_from_dict(data: dict) -> dict[str, dict[str, int]]:
    finishes = data.get("finishes_by_event")
    if finishes:
        return {event: dict(labels) for event, labels in finishes.items()}
    legacy = data.get("finish_histogram")
    if legacy:
        return {"All events": dict(legacy)}
    return {}


def _roster_from_legacy(data: dict) -> list[RosterEntry]:
    if data.get("individual_roster"):
        return [RosterEntry(**r) for r in data["individual_roster"]]
    return [RosterEntry(**r) for r in data.get("roster") or []]


def _summary_from_dict(data: dict) -> TournamentSummary:
    medals_data = data.get("medals") or {}
    highlights_data = data.get("highlights") or []
    gold_winners = _medal_winners_from_dict(medals_data, "gold_winners")
    silver_winners = _medal_winners_from_dict(medals_data, "silver_winners")
    bronze_winners = _medal_winners_from_dict(medals_data, "bronze_winners")
    if not gold_winners and medals_data.get("gold", 0):
        gold_winners = _medal_winners_from_highlights(highlights_data)
    return TournamentSummary(
        medals=MedalCounts(
            gold=medals_data.get("gold", len(gold_winners)),
            silver=medals_data.get("silver", len(silver_winners)),
            bronze=medals_data.get("bronze", len(bronze_winners)),
            gold_winners=gold_winners,
            silver_winners=silver_winners,
            bronze_winners=bronze_winners,
        ),
        finishes_by_event=_finishes_by_event_from_dict(data),
        individual_roster=_roster_from_legacy(data),
        team_roster=[TeamRosterEntry(**t) for t in data.get("team_roster") or []],
        highlights=[Highlight(**h) for h in data.get("highlights") or []],
        total_archers=data.get("total_archers", 0),
        total_events_with_results=data.get("total_events_with_results", 0),
    )
