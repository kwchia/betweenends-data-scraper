import re
from dataclasses import dataclass, field

from app.services.custom_points import (
    CUSTOM_POINTS_MEDAL_MAX_RANK,
    custom_points_counts_for_medals,
    is_award_custom_points_event,
    is_medal_custom_points_event,
)
from app.services.event_parsers import ArcherResult, EventResult, MatchResult, MatchSide

_MATCH_RANK_SUFFIX = re.compile(r"\s+\(\d+\)$")


@dataclass
class MedalCounts:
    gold: int = 0
    silver: int = 0
    bronze: int = 0


@dataclass
class Highlight:
    kind: str
    title: str
    detail: str
    event_name: str


@dataclass
class TournamentSummary:
    medals: MedalCounts = field(default_factory=MedalCounts)
    finish_histogram: dict[str, int] = field(default_factory=dict)
    highlights: list[Highlight] = field(default_factory=list)
    total_archers: int = 0
    total_events_with_results: int = 0


def _archer_identity(name: str) -> str:
    """Normalize display names so the same person counts once across events."""
    normalized = " ".join(name.split())
    normalized = _MATCH_RANK_SUFFIX.sub("", normalized)
    return normalized.casefold()


def count_unique_archers(events: list[EventResult]) -> int:
    seen: set[str] = set()
    for event in events:
        for division in event.divisions:
            for archer in division.archers:
                seen.add(_archer_identity(archer.name))
    return len(seen)


def build_summary(
    events: list[EventResult],
    *,
    count_bracket_medals: bool = True,
) -> TournamentSummary:
    summary = TournamentSummary()
    bracket_medals_applied: set[tuple[str, str, str]] = set()

    for event in events:
        has_results = False
        for division in event.divisions:
            for archer in division.archers:
                has_results = True

                if event.event_type in ("RankingEvent", "CombinedRankingEvent"):
                    _apply_rank_medals(
                        summary, archer.rank, event.event_name, division.name, archer.name
                    )
                    if archer.rank:
                        key = f"Rank {archer.rank}"
                        summary.finish_histogram[key] = summary.finish_histogram.get(key, 0) + 1
                    if (
                        archer.total_score is not None
                        and archer.rank
                        and archer.rank <= CUSTOM_POINTS_MEDAL_MAX_RANK
                    ):
                        summary.highlights.append(
                            Highlight(
                                kind="top_score",
                                title=f"{archer.name} — {archer.total_score}",
                                detail=f"{division.name} in {event.event_name}",
                                event_name=event.event_name,
                            )
                        )
                elif event.event_type == "CustomPointsEvent":
                    if is_award_custom_points_event(event.event_name):
                        continue
                    if not is_medal_custom_points_event(event.event_name):
                        continue
                    if custom_points_counts_for_medals(archer.rank):
                        _apply_rank_medals(
                            summary, archer.rank, event.event_name, division.name, archer.name
                        )
                    if archer.rank and archer.rank <= CUSTOM_POINTS_MEDAL_MAX_RANK:
                        key = f"Rank {archer.rank}"
                        summary.finish_histogram[key] = summary.finish_histogram.get(key, 0) + 1
                        if archer.points is not None:
                            summary.highlights.append(
                                Highlight(
                                    kind="top_score",
                                    title=f"{archer.name} — {archer.points} pts",
                                    detail=f"{division.name} in {event.event_name}",
                                    event_name=event.event_name,
                                )
                            )
                elif event.event_type == "MatchEvent":
                    if count_bracket_medals:
                        medal_key = (event.event_name, division.name, _archer_identity(archer.name))
                        if medal_key not in bracket_medals_applied:
                            bracket_medals_applied.add(medal_key)
                            medal = _bracket_medal_for_archer(archer)
                            if medal:
                                _apply_bracket_medal(
                                    summary, medal, event.event_name, division.name, archer.name
                                )
                    for match in archer.matches:
                        _process_match_highlight(summary, match, event.event_name, archer.name)

        if has_results:
            summary.total_events_with_results += 1

    summary.total_archers = count_unique_archers(events)
    summary.highlights = _dedupe_highlights(summary.highlights)
    summary.highlights.sort(key=lambda h: (h.kind != "comeback", h.kind != "close_match", h.title))
    return summary


def _apply_rank_medals(
    summary: TournamentSummary,
    rank: int | None,
    event_name: str,
    division_name: str,
    archer_name: str,
) -> None:
    if rank == 1:
        summary.medals.gold += 1
        summary.highlights.append(
            Highlight("medal", f"Gold — {archer_name}", f"{division_name} ({event_name})", event_name)
        )
    elif rank == 2:
        summary.medals.silver += 1
        summary.highlights.append(
            Highlight("medal", f"Silver — {archer_name}", f"{division_name} ({event_name})", event_name)
        )
    elif rank == 3:
        summary.medals.bronze += 1
        summary.highlights.append(
            Highlight("medal", f"Bronze — {archer_name}", f"{division_name} ({event_name})", event_name)
        )


def _apply_bracket_medal(
    summary: TournamentSummary,
    medal: str,
    event_name: str,
    division_name: str,
    archer_name: str,
) -> None:
    if medal == "gold":
        summary.medals.gold += 1
        summary.highlights.append(
            Highlight("medal", f"Gold — {archer_name}", f"{division_name} ({event_name})", event_name)
        )
    elif medal == "silver":
        summary.medals.silver += 1
        summary.highlights.append(
            Highlight("medal", f"Silver — {archer_name}", f"{division_name} ({event_name})", event_name)
        )
    elif medal == "bronze":
        summary.medals.bronze += 1
        summary.highlights.append(
            Highlight("medal", f"Bronze — {archer_name}", f"{division_name} ({event_name})", event_name)
        )


def _archer_side_in_match(archer_name: str, match: MatchResult) -> MatchSide | None:
    for side in match.sides:
        if side.name.startswith(archer_name) or archer_name in side.name:
            return side
    return match.sides[0] if match.sides else None


def _is_finals_stage_round(round_name: str, round_index: int) -> bool:
    if round_name in ("Finals Round", "Match 0"):
        return True
    return round_index == 0 and round_name.startswith("Match ")


def _is_semifinal_round(round_name: str, round_index: int) -> bool:
    if "Semi" in round_name and "quarter" not in round_name.lower():
        return True
    return round_index == 1 and round_name.startswith("Match ")


def match_bracket_placement(archer: ArcherResult) -> int | None:
    """Derive elimination podium finish from bracket results.

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
    final_side = _archer_side_in_match(archer.name, final_match)
    if final_side is None:
        return None
    won_final = final_side.won

    semi_matches = [
        m
        for m in archer.matches
        if _is_semifinal_round(m.round_name, m.round_index)
    ]
    if semi_matches:
        semi_side = _archer_side_in_match(archer.name, semi_matches[0])
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


def _bracket_round_tier(round_name: str) -> str:
    """Classify bracket round for medal placement (finals > semi > quarter > early)."""
    name = (round_name or "").strip().lower()
    if name in ("finals round", "match 0"):
        return "finals"
    if name.startswith("match "):
        return "finals"
    if "bronze" in name:
        return "bronze_match"
    if "semi" in name and "quarter" not in name:
        return "semi"
    if "quarter" in name or "1/8" in name or "round of 16" in name:
        return "quarter"
    if any(x in name for x in ("1/16", "1/32", "1/64", "1/128", "round of 32", "round of 64")):
        return "early"
    return "other"


def _bracket_medal_for_archer(archer: ArcherResult) -> str | None:
    """Podium medal from elimination bracket (at most one per archer per bracket).

    Gold: bracket champion. Silver: lost in the final. Bronze: lost in the semifinal
  (3rd place). Losses in quarterfinals or earlier do not earn a medal.
    """
    if not archer.matches:
        return None

    place = match_bracket_placement(archer)
    if place == 1:
        return "gold"
    if place == 2:
        return "silver"
    if place == 3:
        return "bronze"
    if place == 4:
        return None

    ordered = sorted(archer.matches, key=lambda m: -m.round_index)
    loss_match = None
    for match in ordered:
        side = _archer_side_in_match(archer.name, match)
        if side and not side.won:
            loss_match = match
            break

    if loss_match is None:
        return "gold"

    tier = _bracket_round_tier(loss_match.round_name)
    if tier == "finals":
        return "silver"
    if tier == "semi":
        return "bronze"
  # bronze medal match winner/loser handled below if needed
    if tier == "bronze_match":
        side = _archer_side_in_match(archer.name, loss_match)
        if side and side.won:
            return "bronze"
    return None


def _process_match_highlight(
    summary: TournamentSummary,
    match: MatchResult,
    event_name: str,
    archer_name: str,
) -> None:
    if len(match.sides) < 2:
        return
    ours = _archer_side_in_match(archer_name, match) or match.sides[0]
    opp = match.sides[1] if match.sides[0] is ours else match.sides[0]

    summary.finish_histogram[match.round_name] = summary.finish_histogram.get(match.round_name, 0) + 1

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


def medal_highlights_by_tier(summary: TournamentSummary) -> dict[str, list[Highlight]]:
    """Medal highlights grouped for the summary tab (gold / silver / bronze)."""
    tiers: dict[str, list[Highlight]] = {"gold": [], "silver": [], "bronze": []}
    for highlight in summary.highlights:
        if highlight.kind != "medal":
            continue
        if highlight.title.startswith("Gold"):
            tiers["gold"].append(highlight)
        elif highlight.title.startswith("Silver"):
            tiers["silver"].append(highlight)
        elif highlight.title.startswith("Bronze"):
            tiers["bronze"].append(highlight)
    return tiers


def _dedupe_highlights(highlights: list[Highlight]) -> list[Highlight]:
    seen = set()
    out = []
    for h in highlights:
        key = (h.kind, h.title, h.detail)
        if key not in seen:
            seen.add(key)
            out.append(h)
    return out[:30]
