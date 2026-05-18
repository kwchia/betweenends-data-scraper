import re
from dataclasses import dataclass, field

from app.services.club_filter import normalize_for_match
from app.services.event_parsers import ArcherResult, EventResult, MatchResult, MatchSide

_MATCH_RANK_SUFFIX = re.compile(r"\s+\(\d+\)$")
_INDIVIDUAL_EVENT_TYPES = frozenset({"RankingEvent", "CombinedRankingEvent", "MatchEvent"})
_RANKING_HIGHLIGHT_MAX_PLACE = 10


@dataclass
class MedalWinner:
    archer_name: str
    event_name: str
    detail: str


@dataclass
class MedalCounts:
    gold: int = 0
    silver: int = 0
    bronze: int = 0
    gold_winners: list[MedalWinner] = field(default_factory=list)
    silver_winners: list[MedalWinner] = field(default_factory=list)
    bronze_winners: list[MedalWinner] = field(default_factory=list)


@dataclass
class RosterEntry:
    name: str
    categories: list[str] = field(default_factory=list)


@dataclass
class TeamRosterEntry:
    event_name: str
    category: str
    rank: int | None = None
    points: float | None = None


@dataclass
class Highlight:
    kind: str
    title: str
    detail: str
    event_name: str


@dataclass
class TournamentSummary:
    medals: MedalCounts = field(default_factory=MedalCounts)
    finishes_by_event: dict[str, dict[str, int]] = field(default_factory=dict)
    individual_roster: list[RosterEntry] = field(default_factory=list)
    team_roster: list[TeamRosterEntry] = field(default_factory=list)
    highlights: list[Highlight] = field(default_factory=list)
    total_archers: int = 0
    total_events_with_results: int = 0


def _archer_identity(name: str) -> str:
    """Normalize display names so the same person counts once across events."""
    return _display_name(name).casefold()


def _display_name(name: str) -> str:
    normalized = " ".join(name.split())
    return _MATCH_RANK_SUFFIX.sub("", normalized).strip()


def _coerce_rank(rank) -> int | None:
    if rank is None:
        return None
    try:
        return int(rank)
    except (TypeError, ValueError):
        return None


def _is_custom_points_team_result(archer: ArcherResult) -> bool:
    name = _display_name(archer.name)
    if any(marker in name for marker in ("University", "College", " Institute", " School", " Team")):
        return True
    if archer.club:
        club_n = normalize_for_match(archer.club)
        name_n = normalize_for_match(name)
        if name_n == club_n or club_n in name_n or name_n in club_n:
            return True
    return False


def is_team_entry(archer: ArcherResult, event_type: str) -> bool:
    if event_type == "CustomPointsEvent":
        return _is_custom_points_team_result(archer)
    if event_type != "MatchEvent":
        return False
    name = archer.name
    if "\n[" in name or " [" in name:
        return True
    if name.endswith(" Team"):
        return True
    if archer.club and normalize_for_match(_display_name(name)) == normalize_for_match(archer.club):
        return True
    return False


def build_individual_roster(events: list[EventResult]) -> list[RosterEntry]:
    by_identity: dict[str, tuple[str, set[str]]] = {}
    for event in events:
        if event.event_type not in _INDIVIDUAL_EVENT_TYPES:
            continue
        for division in event.divisions:
            for archer in division.archers:
                if is_team_entry(archer, event.event_type):
                    continue
                identity = _archer_identity(archer.name)
                display = _display_name(archer.name)
                if identity not in by_identity:
                    by_identity[identity] = (display, set())
                elif "(" in by_identity[identity][0] and "(" not in display:
                    by_identity[identity] = (display, by_identity[identity][1])
                by_identity[identity][1].add(division.name)

    roster = [
        RosterEntry(name=name, categories=sorted(categories))
        for name, categories in by_identity.values()
    ]
    roster.sort(key=lambda e: ((e.categories[0].lower() if e.categories else ""), e.name.lower()))
    return roster


def build_team_roster(events: list[EventResult]) -> list[TeamRosterEntry]:
    seen: set[tuple[str, str]] = set()
    teams: list[TeamRosterEntry] = []
    for event in events:
        for division in event.divisions:
            for archer in division.archers:
                if not is_team_entry(archer, event.event_type):
                    continue
                key = (event.event_name, division.name)
                if key in seen:
                    continue
                seen.add(key)
                teams.append(
                    TeamRosterEntry(
                        event_name=event.event_name,
                        category=division.name,
                        rank=_coerce_rank(archer.rank),
                        points=archer.points,
                    )
                )
    teams.sort(key=lambda t: (t.event_name.lower(), t.category.lower()))
    return teams


def count_unique_archers(events: list[EventResult]) -> int:
    seen: set[str] = set()
    for event in events:
        if event.event_type not in _INDIVIDUAL_EVENT_TYPES:
            continue
        for division in event.divisions:
            for archer in division.archers:
                if is_team_entry(archer, event.event_type):
                    continue
                seen.add(_archer_identity(archer.name))
    return len(seen)


def build_summary(events: list[EventResult]) -> TournamentSummary:
    summary = TournamentSummary()

    for event in events:
        has_results = False
        for division in event.divisions:
            for archer in division.archers:
                has_results = True

                if event.event_type in ("RankingEvent", "CombinedRankingEvent", "CustomPointsEvent"):
                    rank = _coerce_rank(archer.rank)
                    detail = (
                        f"{event.event_name}"
                        if event.event_type == "CustomPointsEvent"
                        else division.name
                    )
                    _apply_rank_medals(summary, rank, event.event_name, detail, archer.name)
                    if rank:
                        _record_finish(summary, event.event_name, f"Rank {rank}")
                    if event.event_type in ("RankingEvent", "CombinedRankingEvent"):
                        _maybe_add_ranking_highlight(
                            summary,
                            archer,
                            rank,
                            division.name,
                            event.event_name,
                        )
                elif event.event_type == "MatchEvent":
                    _apply_match_bracket_medals(
                        summary, archer, event.event_name, division.name
                    )
                    for match in archer.matches:
                        _process_match_highlight(
                            summary,
                            match,
                            event.event_name,
                            division.name,
                            archer,
                            event.event_type,
                        )

        if has_results:
            summary.total_events_with_results += 1

    summary.total_archers = count_unique_archers(events)
    summary.individual_roster = build_individual_roster(events)
    summary.team_roster = build_team_roster(events)
    summary.highlights = _dedupe_highlights(summary.highlights)
    summary.highlights.sort(
        key=lambda h: (
            h.kind != "medal",
            h.kind != "top_finish",
            h.kind != "comeback",
            h.kind != "close_match",
            h.title,
        )
    )
    return summary


def _ordinal(rank: int) -> str:
    if 10 <= rank % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(rank % 10, "th")
    return f"{rank}{suffix}"


def _maybe_add_ranking_highlight(
    summary: TournamentSummary,
    archer: ArcherResult,
    rank: int | None,
    division_name: str,
    event_name: str,
) -> None:
    if not rank or rank > _RANKING_HIGHLIGHT_MAX_PLACE:
        return
    score_fragment = f" ({archer.total_score} pts)" if archer.total_score is not None else ""
    summary.highlights.append(
        Highlight(
            kind="top_finish",
            title=f"{archer.name} — {_ordinal(rank)}",
            detail=f"{division_name} in {event_name}{score_fragment}",
            event_name=event_name,
        )
    )


def _record_finish(summary: TournamentSummary, event_name: str, label: str) -> None:
    event_finishes = summary.finishes_by_event.setdefault(event_name, {})
    event_finishes[label] = event_finishes.get(label, 0) + 1


def _record_medal(
    summary: TournamentSummary,
    tier: str,
    archer_name: str,
    event_name: str,
    detail: str,
) -> None:
    winner = MedalWinner(archer_name=archer_name, event_name=event_name, detail=detail)
    winners = getattr(summary.medals, f"{tier}_winners")
    winners.append(winner)
    setattr(summary.medals, tier, getattr(summary.medals, tier) + 1)
    if tier == "gold":
        summary.highlights.append(
            Highlight("medal", f"Gold — {archer_name}", f"{detail} ({event_name})", event_name)
        )


def _apply_rank_medals(
    summary: TournamentSummary,
    rank: int | None,
    event_name: str,
    detail: str,
    archer_name: str,
) -> None:
    if rank == 1:
        _record_medal(summary, "gold", archer_name, event_name, detail)
    elif rank == 2:
        _record_medal(summary, "silver", archer_name, event_name, detail)
    elif rank == 3:
        _record_medal(summary, "bronze", archer_name, event_name, detail)


def _is_finals_stage_round(round_name: str, round_index: int) -> bool:
    if round_name in ("Finals Round", "Match 0"):
        return True
    return round_index == 0 and round_name.startswith("Match ")


def _is_semifinal_round(round_name: str, round_index: int) -> bool:
    if "Semi" in round_name:
        return True
    return round_index == 1 and round_name.startswith("Match ")


def _archer_side_in_match(match: MatchResult, archer_name: str) -> MatchSide | None:
    for side in match.sides:
        if side.name.startswith(archer_name) or archer_name in side.name:
            return side
    return match.sides[0] if match.sides else None


def match_bracket_placement(archer: ArcherResult) -> int | None:
    """
    Derive elimination podium finish from bracket results.

    Gold: won semifinal and final (gold-medal match).
    Silver: won semifinal, lost final.
    Bronze: lost semifinal, won the bronze-medal match (also in the finals stage).
    4th: lost semifinal and bronze-medal match.
  """
    if not archer.matches:
        return None

    finals_matches = [
        m
        for m in archer.matches
        if _is_finals_stage_round(m.round_name, m.round_index)
    ]
    if not finals_matches:
        return None

    final_match = finals_matches[0]
    final_side = _archer_side_in_match(final_match, archer.name)
    if final_side is None:
        return None
    won_final = final_side.won

    semi_matches = [
        m
        for m in archer.matches
        if _is_semifinal_round(m.round_name, m.round_index)
    ]
    if semi_matches:
        semi_side = _archer_side_in_match(semi_matches[0], archer.name)
        won_semi = semi_side.won if semi_side else False
    else:
        won_semi = True

    if won_semi and won_final:
        return 1
    if won_semi and not won_final:
        return 2
    if not won_semi and won_final:
        return 3
    return 4


def _apply_match_bracket_medals(
    summary: TournamentSummary,
    archer: ArcherResult,
    event_name: str,
    division_name: str,
) -> None:
    place = match_bracket_placement(archer)
    if place is None:
        return

    detail = division_name
    if place == 1:
        _record_medal(summary, "gold", archer.name, event_name, detail)
        _record_finish(summary, event_name, "1st place")
    elif place == 2:
        _record_medal(summary, "silver", archer.name, event_name, detail)
        _record_finish(summary, event_name, "2nd place")
    elif place == 3:
        _record_medal(summary, "bronze", archer.name, event_name, detail)
        _record_finish(summary, event_name, "3rd place")
    elif place == 4:
        _record_finish(summary, event_name, "4th place")


def _process_match_highlight(
    summary: TournamentSummary,
    match: MatchResult,
    event_name: str,
    division_name: str,
    archer: ArcherResult,
    event_type: str,
) -> None:
    if len(match.sides) < 2:
        return
    archer_name = archer.name
    ours = next(
        (s for s in match.sides if s.name.startswith(archer_name) or archer_name in s.name),
        match.sides[0],
    )
    opp = match.sides[1] if match.sides[0] is ours else match.sides[0]

    _record_finish(summary, event_name, match.round_name)

    if is_team_entry(archer, event_type):
        return

    if ours.won and _was_comeback(ours, opp):
        summary.highlights.append(
            Highlight(
                kind="comeback",
                title=f"Comeback win — {archer_name}",
                detail=f"{match.round_name}: {ours.total} vs {opp.total} ({event_name})",
                event_name=event_name,
            )
        )

    if abs(ours.total - opp.total) == 1:
        summary.highlights.append(
            Highlight(
                kind="close_match",
                title=f"Close match — {archer_name}",
                detail=f"{match.round_name}: {ours.total}-{opp.total} ({event_name})",
                event_name=event_name,
            )
        )


def _was_comeback(ours, opp) -> bool:
    trailing = False
    our_running = 0
    opp_running = 0
    for e in ours.end_scores:
        if not e.display:
            continue
        our_pts = _parse_set_points(e.display)
        opp_idx = e.end_number - 1
        opp_display = opp.end_scores[opp_idx].display if opp_idx < len(opp.end_scores) else ""
        opp_pts = _parse_set_points(opp_display)
        our_running += our_pts
        opp_running += opp_pts
        if opp_running > our_running:
            trailing = True
    return trailing and ours.won


def _parse_set_points(display: str) -> int:
    if "(" in display:
        try:
            return int(display.split("(")[1].rstrip(")"))
        except ValueError:
            return 0
    try:
        return int(display) if display else 0
    except ValueError:
        return 0


def _dedupe_highlights(highlights: list[Highlight]) -> list[Highlight]:
    seen = set()
    out = []
    for h in highlights:
        key = (h.kind, h.title, h.detail)
        if key not in seen:
            seen.add(key)
            out.append(h)
    return out[:30]
