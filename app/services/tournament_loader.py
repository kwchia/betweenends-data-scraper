from app.models import Club
from app.services.archer_filter import ArcherIdentity
from app.services.betweenends_client import BetweenendsAPIError, BetweenendsClient
from app.services.club_filter import AliasRule
from app.services.event_parsers import EventResult, parse_event
from app.services.summary import TournamentSummary, build_summary


def club_alias_rules(club: Club) -> list[AliasRule]:
    aliases = [AliasRule(alias=a.alias, match_mode=a.match_mode) for a in club.aliases]
    if not aliases:
        aliases = [AliasRule(alias=club.name, match_mode="contains")]
    return aliases


def fetch_tournament_results(
    client: BetweenendsClient,
    tournament_id: int,
    aliases: list[AliasRule],
) -> tuple[dict, list[EventResult], TournamentSummary]:
    tournament = client.get_tournament(tournament_id)
    events_meta = sorted(tournament.get("events") or [], key=lambda e: e.get("display_order", 0))
    parsed_events: list[EventResult] = []

    for event_meta in events_meta:
        event_id = event_meta["id"]
        event_type = event_meta.get("event_type", "")
        try:
            event_data = client.get_event(event_id)
            scores_data = None
            if event_type in ("RankingEvent", "CombinedRankingEvent", "MatchEvent"):
                scores_data = client.get_event_scores(event_id)
            parsed = parse_event(event_meta, event_data, scores_data, aliases)
            if parsed.divisions:
                parsed_events.append(parsed)
        except BetweenendsAPIError:
            continue

    summary = build_summary(parsed_events, club_roster=True)
    return tournament, parsed_events, summary


def fetch_archer_tournament_results(
    client: BetweenendsClient,
    tournament_id: int,
    identity: ArcherIdentity,
) -> tuple[dict, list[EventResult], TournamentSummary]:
    tournament = client.get_tournament(tournament_id)
    events_meta = sorted(tournament.get("events") or [], key=lambda e: e.get("display_order", 0))
    parsed_events: list[EventResult] = []

    for event_meta in events_meta:
        event_id = event_meta["id"]
        event_type = event_meta.get("event_type", "")
        try:
            event_data = client.get_event(event_id)
            scores_data = None
            if event_type in ("RankingEvent", "CombinedRankingEvent", "MatchEvent"):
                scores_data = client.get_event_scores(event_id)
            parsed = parse_event(
                event_meta, event_data, scores_data, archer_identity=identity
            )
            if parsed.divisions:
                parsed_events.append(parsed)
        except BetweenendsAPIError:
            continue

    summary = build_summary(parsed_events)
    return tournament, parsed_events, summary
