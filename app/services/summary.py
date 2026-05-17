import re
from dataclasses import dataclass, field

from app.services.event_parsers import EventResult, MatchResult

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


def build_summary(events: list[EventResult]) -> TournamentSummary:
    summary = TournamentSummary()

    for event in events:
        has_results = False
        for division in event.divisions:
            for archer in division.archers:
                has_results = True

                if event.event_type in ("RankingEvent", "CombinedRankingEvent", "CustomPointsEvent"):
                    _apply_rank_medals(summary, archer.rank, event.event_name, division.name, archer.name)
                    if archer.rank:
                        key = f"Rank {archer.rank}"
                        summary.finish_histogram[key] = summary.finish_histogram.get(key, 0) + 1
                    if archer.total_score is not None:
                        summary.highlights.append(
                            Highlight(
                                kind="top_score",
                                title=f"{archer.name} — {archer.total_score}",
                                detail=f"{division.name} in {event.event_name}",
                                event_name=event.event_name,
                            )
                        )
                elif event.event_type == "MatchEvent":
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
    elif rank == 3:
        summary.medals.bronze += 1


def _process_match_highlight(
    summary: TournamentSummary,
    match: MatchResult,
    event_name: str,
    archer_name: str,
) -> None:
    if len(match.sides) < 2:
        return
    ours = next((s for s in match.sides if s.name.startswith(archer_name) or archer_name in s.name), match.sides[0])
    opp = match.sides[1] if match.sides[0] is ours else match.sides[0]

    if ours.won and match.round_name in ("Finals Round", "Match 0"):
        summary.medals.gold += 1
    elif ours.won and "Semi" in match.round_name:
        summary.medals.silver += 1
    elif ours.won and ("Quarter" in match.round_name or "1/8" in match.round_name):
        summary.medals.bronze += 1

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


def _dedupe_highlights(highlights: list[Highlight]) -> list[Highlight]:
    seen = set()
    out = []
    for h in highlights:
        key = (h.kind, h.title, h.detail)
        if key not in seen:
            seen.add(key)
            out.append(h)
    return out[:30]
