"""Short narrative summaries for division, archer, and match result sections."""

from __future__ import annotations

from app.services.event_parsers import ArcherResult, DivisionResult, EventResult, MatchResult, MatchSide

_ROUND_LABELS: dict[str, str] = {
    "Finals Round": "the final",
    "Semi Finals": "the semifinals",
    "Quarter Finals": "the quarterfinals",
    "1/8th Round": "the round of 16",
    "1/16th Round": "the round of 32",
    "1/32nd Round": "the round of 64",
    "1/64th Round": "the round of 128",
}


def summarize_division(event: EventResult, division: DivisionResult) -> str:
    if not division.archers:
        return ""

    if event.event_type in ("RankingEvent", "CombinedRankingEvent"):
        return _summarize_ranking_division(division)
    if event.event_type == "CustomPointsEvent":
        return _summarize_points_division(division)
    if event.event_type == "MatchEvent":
        return _summarize_match_division(division)
    return ""


def summarize_archer(event: EventResult, archer: ArcherResult) -> str:
    if event.event_type in ("RankingEvent", "CombinedRankingEvent"):
        return _summarize_ranking_archer(archer)
    if event.event_type == "CustomPointsEvent":
        return _summarize_points_archer(archer)
    if event.event_type == "MatchEvent":
        return _summarize_match_path(archer)
    return ""


def summarize_match(match: MatchResult, archer_name: str) -> str:
    side = _archer_side(match, archer_name)
    if not side:
        return match.round_name
    opp = _opponent_side(match, side)
    verb = "Beat" if side.won else "Lost to"
    opp_name = _short_label(opp.name)
    return f"{verb} {opp_name} {side.total}–{opp.total}"


def _summarize_ranking_division(division: DivisionResult) -> str:
    archers = sorted(division.archers, key=lambda a: a.rank or 9999)
    if len(archers) == 1:
        return _summarize_ranking_archer(archers[0])

    best = archers[0]
    best_text = _summarize_ranking_archer(best)
    if len(archers) == 2:
        other = archers[1]
        return f"{best_text}; {_short_label(other.name)} finished {_ordinal(other.rank)}."

    others = ", ".join(f"{_ordinal(a.rank)} ({_short_label(a.name)})" for a in archers[1:3])
    extra = f" and {len(archers) - 3} more" if len(archers) > 3 else ""
    return f"{len(archers)} archers — best: {best_text[0].lower()}{best_text[1:]}; also {others}{extra}."


def _summarize_ranking_archer(archer: ArcherResult) -> str:
    if archer.rank is None:
        return f"{archer.name} competed in qualifying."
    if archer.total_score is not None:
        return f"{_short_label(archer.name)} finished {_ordinal(archer.rank)} with {archer.total_score} points."
    return f"{_short_label(archer.name)} finished {_ordinal(archer.rank)}."


def _summarize_points_division(division: DivisionResult) -> str:
    archers = sorted(division.archers, key=lambda a: a.rank or 9999)
    if len(archers) == 1:
        return _summarize_points_archer(archers[0])
    leader = archers[0]
    return (
        f"{len(archers)} teams — leader: {_short_label(leader.name)} "
        f"({_ordinal(leader.rank)}{_points_fragment(leader)})."
    )


def _summarize_points_archer(archer: ArcherResult) -> str:
    if archer.rank is None:
        return f"{_short_label(archer.name)} recorded team points."
    return f"{_short_label(archer.name)} ranked {_ordinal(archer.rank)}{_points_fragment(archer)}."


def _summarize_match_division(division: DivisionResult) -> str:
    parts = []
    for archer in division.archers:
        path = _summarize_match_path(archer).rstrip(".")
        if not path:
            continue
        label = _short_label(archer.name)
        if len(division.archers) == 1:
            parts.append(path[0].upper() + path[1:])
        else:
            parts.append(f"{label}: {path[0].lower()}{path[1:]}")
    return ". ".join(parts) + "." if parts else ""


def _summarize_match_path(archer: ArcherResult) -> str:
    if not archer.matches:
        return "No bracket matches recorded."

    ordered = sorted(archer.matches, key=lambda m: -m.round_index)
    loss_index = None
    for i, match in enumerate(ordered):
        side = _archer_side(match, archer.name)
        if side and not side.won:
            loss_index = i
            break

    if loss_index is None:
        deepest = ordered[-1]
        if len(ordered) == 1:
            return f"Won {_round_phrase(deepest.round_name, with_article=False)}."
        return (
            f"Won all {len(ordered)} matches, through {_round_phrase(deepest.round_name)}."
        )

    loss_match = ordered[loss_index]
    if loss_index == 0:
        return f"Eliminated in {_round_phrase(loss_match.round_name)}."

    first_win = ordered[0]
    if loss_index == 1:
        return (
            f"Won {_round_phrase(first_win.round_name, with_article=False)} but was "
            f"eliminated in {_round_phrase(loss_match.round_name)}."
        )

    won_labels = [_round_phrase(m.round_name, with_article=False) for m in ordered[:loss_index]]
    if len(won_labels) == 2:
        won_text = f"{won_labels[0]} and {won_labels[1]}"
    else:
        won_text = ", ".join(won_labels[:-1]) + f", and {won_labels[-1]}"
    return f"Won {won_text}, then was eliminated in {_round_phrase(loss_match.round_name)}."


def _archer_side(match: MatchResult, archer_name: str) -> MatchSide | None:
    for side in match.sides:
        if side.name.startswith(archer_name) or archer_name in side.name:
            return side
    return match.sides[0] if match.sides else None


def _opponent_side(match: MatchResult, ours: MatchSide) -> MatchSide:
    if len(match.sides) < 2:
        return match.sides[0]
    return match.sides[1] if match.sides[0] is ours else match.sides[0]


def _round_phrase(round_name: str, *, with_article: bool = True) -> str:
    label = _ROUND_LABELS.get(round_name)
    if label:
        return label if with_article else label.removeprefix("the ")
    if round_name.startswith("Match "):
        num = round_name.replace("Match ", "").strip()
        phrase = f"match {num}"
        return f"the {phrase}" if with_article else phrase
    lowered = round_name.lower()
    return f"the {lowered}" if with_article else lowered


def _ordinal(rank: int | None) -> str:
    if rank is None:
        return "—"
    if 10 <= rank % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(rank % 10, "th")
    return f"{rank}{suffix}"


def _points_fragment(archer: ArcherResult) -> str:
    if archer.points is None:
        return ""
    if float(archer.points).is_integer():
        return f" with {int(archer.points)} points"
    return f" with {archer.points:.1f} points"


def _short_label(name: str) -> str:
    text = name.strip()
    if " (" in text:
        text = text.split(" (", 1)[0]
    if "\n" in text:
        text = text.replace("\n", " ").split("[", 1)[0].strip()
    return text
