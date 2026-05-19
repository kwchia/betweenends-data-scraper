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
    TournamentSummary,
    collect_club_roster,
    unique_archer_names,
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


def load_snapshot(
    data: dict, *, club_roster: bool = False
) -> tuple[dict, list[EventResult], TournamentSummary]:
    tournament = data.get("tournament") or {}
    events = [_event_from_dict(e) for e in data.get("events") or []]
    summary = _summary_from_dict(data.get("summary") or {})
    if club_roster:
        summary.roster = collect_club_roster(events)
    else:
        summary.roster = unique_archer_names(events)
    summary.total_archers = len(summary.roster)
    return tournament, events, summary


def _event_from_dict(data: dict) -> EventResult:
    return EventResult(
        event_id=data["event_id"],
        event_name=data["event_name"],
        event_type=data["event_type"],
        display_order=data.get("display_order", 0),
        divisions=[_division_from_dict(d) for d in data.get("divisions") or []],
        arrows_per_end=data.get("arrows_per_end"),
        ends_per_round=data.get("ends_per_round"),
        num_rounds=data.get("num_rounds"),
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
        aid=data.get("aid"),
        arrow_string=data.get("arrow_string"),
        round_arrow_strings=data.get("round_arrow_strings") or [],
        match_reason=data.get("match_reason"),
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
        arrow_string=data.get("arrow_string"),
    )


def _summary_from_dict(data: dict) -> TournamentSummary:
    medals_data = data.get("medals") or {}
    return TournamentSummary(
        medals=MedalCounts(
            gold=medals_data.get("gold", 0),
            silver=medals_data.get("silver", 0),
            bronze=medals_data.get("bronze", 0),
        ),
        finish_histogram=data.get("finish_histogram") or {},
        highlights=[Highlight(**h) for h in data.get("highlights") or []],
        roster=list(data.get("roster") or []),
        total_archers=data.get("total_archers", 0),
        total_events_with_results=data.get("total_events_with_results", 0),
    )
