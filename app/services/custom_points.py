"""Classify CustomPointsEvent payloads for medals vs awards vs component rows."""

import re

# Events that are awards/honors, not podium medals.
_AWARD_EVENT_PATTERNS = (
    re.compile(r"all[\s-]*american", re.I),
    re.compile(r"all[\s-]*around", re.I),
    re.compile(r"archer(?:s)?\s+of\s+the\s+year", re.I),
    re.compile(r"all[\s-]*region\s+team", re.I),
    re.compile(r"scholar", re.I),
)

# Events whose final row is an overall team championship standing (medal-eligible).
_MEDAL_EVENT_PATTERNS = (
    re.compile(r"overall\s+team", re.I),
    re.compile(r"team\s+championship", re.I),
    re.compile(r"overall.*championship", re.I),
    re.compile(r"championship\s+points", re.I),
)

CUSTOM_POINTS_MEDAL_MAX_RANK = 10


def is_award_custom_points_event(event_name: str) -> bool:
    name = event_name or ""
    return any(p.search(name) for p in _AWARD_EVENT_PATTERNS)


def is_medal_custom_points_event(event_name: str) -> bool:
    """Team/overall championship point totals (not honor rolls like All-American)."""
    if is_award_custom_points_event(event_name):
        return False
    name = event_name or ""
    return any(p.search(name) for p in _MEDAL_EVENT_PATTERNS)


def custom_points_counts_for_medals(rank: int | None) -> bool:
    if rank is None or rank > CUSTOM_POINTS_MEDAL_MAX_RANK:
        return False
    return rank <= 3


def overall_standings_rows(rows: list[dict]) -> list[dict]:
    """Keep only the cumulative overall row(s), not per-discipline point components."""
    scored = [r for r in rows if r and r.get("scores")]
    if not scored:
        return []
    if len(scored) == 1:
        return scored
    return [scored[-1]]
