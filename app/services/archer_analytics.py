"""Analytics over saved archer tournament snapshots."""

from dataclasses import dataclass, field
from statistics import mean
from typing import Optional

from app.services import scoring
from app.services.archer_metadata import distance_for_round
from app.services.event_parsers import ArcherResult, EventResult, MatchResult
from app.services.snapshot import load_snapshot


@dataclass
class ScorePoint:
    date: str
    tournament_name: str
    event_name: str
    division: str
    score: float
    distance: str
    normalized: float
    round_index: int = 0


@dataclass
class ConsistencyPoint:
    date: str
    tournament_name: str
    event_name: str
    end_spread_avg: float
    flier_rate: float


@dataclass
class EliminationStats:
    round_name: str
    round_index: int
    event_name: str
    tournament_name: str
    wins: int
    losses: int
    win_rate: float
    avg_arrows: float
    vs_higher_seed_wins: int
    vs_higher_seed_total: int
    vs_lower_seed_wins: int
    vs_lower_seed_total: int


@dataclass
class ArcherAnalytics:
    scores_by_distance: dict[str, list[ScorePoint]] = field(default_factory=dict)
    normalized_scores: list[ScorePoint] = field(default_factory=list)
    consistency: list[ConsistencyPoint] = field(default_factory=list)
    elimination: list[EliminationStats] = field(default_factory=list)


def _arrow_value(char: str) -> int:
    return scoring.ARROW_VALUES.get(char, 0)


def _end_values(arrow_string: str, arrows_per_end: int) -> list[list[int]]:
    if not arrow_string or arrows_per_end < 1:
        return []
    ends = []
    for i in range(0, len(arrow_string), arrows_per_end):
        chunk = arrow_string[i : i + arrows_per_end]
        if chunk:
            ends.append([_arrow_value(c) for c in chunk])
    return ends


def _end_spread(end_arrows: list[int]) -> float:
    if len(end_arrows) < 2:
        return 0.0
    return float(max(end_arrows) - min(end_arrows))


def _fliers_in_end(end_arrows: list[int]) -> int:
    if len(end_arrows) < 2:
        return 0
    med = sorted(end_arrows)[len(end_arrows) // 2]
    return sum(1 for v in end_arrows if v <= med - 2)


def _normalized_score(score: int, arrow_count: int) -> float:
    if arrow_count <= 0:
        return 0.0
    return score / (arrow_count * 10)


def _append_consistency(
    analytics: ArcherAnalytics,
    date: str,
    tournament_name: str,
    event_name: str,
    arrow_string: str,
    arrows_per_end: int,
) -> None:
    ends = _end_values(arrow_string, arrows_per_end)
    if not ends:
        return
    spreads = [_end_spread(e) for e in ends]
    fliers = sum(_fliers_in_end(e) for e in ends)
    analytics.consistency.append(
        ConsistencyPoint(
            date=date,
            tournament_name=tournament_name,
            event_name=event_name,
            end_spread_avg=mean(spreads),
            flier_rate=fliers / len(ends),
        )
    )


def _archer_side_in_match(archer_name: str, match: MatchResult):
    for side in match.sides:
        base = side.name.split(" (")[0].strip()
        if archer_name.startswith(base) or base in archer_name:
            return side
    return match.sides[0] if match.sides else None


def _opponent_side(archer_side, match: MatchResult):
    for side in match.sides:
        if side is not archer_side:
            return side
    return None


def build_analytics(
    saved_entries: list,
    practices: Optional[list] = None,
    include_practice: bool = True,
) -> ArcherAnalytics:
    analytics = ArcherAnalytics()
    elim_buckets: dict[tuple[str, int], dict] = {}

    for entry in saved_entries:
        tournament, events, _ = load_snapshot(entry.snapshot_json)
        date = entry.start_date or tournament.get("start_date") or ""
        t_name = entry.tournament_name

        for event in events:
            for division in event.divisions:
                for archer in division.archers:
                    _process_ranking(
                        analytics,
                        entry,
                        event,
                        division.name,
                        archer,
                        date,
                        t_name,
                    )
                    _process_custom_points(
                        analytics,
                        event,
                        division.name,
                        archer,
                        date,
                        t_name,
                    )
                    _process_matches(
                        analytics,
                        archer,
                        date,
                        t_name,
                        event.event_name,
                        elim_buckets,
                    )

    if include_practice and practices:
        from app.services.archer_practice import practice_arrow_rounds, practice_to_score_points

        for practice in practices:
            if not practice.include_in_analytics:
                continue
            for point in practice_to_score_points(practice):
                analytics.normalized_scores.append(point)
                analytics.scores_by_distance.setdefault(point.distance, []).append(point)
            for date, name, arrow_string, ape in practice_arrow_rounds(practice):
                _append_consistency(
                    analytics, date, name, "Practice", arrow_string, ape
                )

    for bucket_key in sorted(
        elim_buckets.keys(),
        key=lambda k: (elim_buckets[k]["tournament_name"], -k[1]),
    ):
        bucket = elim_buckets[bucket_key]
        total = bucket["wins"] + bucket["losses"]
        analytics.elimination.append(
            EliminationStats(
                round_name=bucket["round_name"],
                round_index=bucket_key[1],
                event_name=bucket["event_name"],
                tournament_name=bucket["tournament_name"],
                wins=bucket["wins"],
                losses=bucket["losses"],
                win_rate=bucket["wins"] / total if total else 0.0,
                avg_arrows=(
                    mean(bucket["arrow_totals"]) if bucket["arrow_totals"] else 0.0
                ),
                vs_higher_seed_wins=bucket["vs_higher_wins"],
                vs_higher_seed_total=bucket["vs_higher_total"],
                vs_lower_seed_wins=bucket["vs_lower_wins"],
                vs_lower_seed_total=bucket["vs_lower_total"],
            )
        )

    return analytics


def _process_ranking(
    analytics: ArcherAnalytics,
    entry,
    event: EventResult,
    division_name: str,
    archer: ArcherResult,
    date: str,
    t_name: str,
) -> None:
    if event.event_type not in ("RankingEvent", "CombinedRankingEvent"):
        return
    ape = event.arrows_per_end or 3
    epr = event.ends_per_round or 1
    arrows_per_end = ape
    arrows_per_round = ape * epr

    rounds = archer.round_arrow_strings or (
        [archer.arrow_string] if archer.arrow_string else []
    )
    if not rounds and archer.arrow_string:
        num_rounds = event.num_rounds or 1
        rounds = [
            archer.arrow_string[r * arrows_per_round : (r + 1) * arrows_per_round]
            for r in range(num_rounds)
        ]

    for round_index, round_arrows in enumerate(rounds):
        if not round_arrows:
            continue
        score = scoring.calculate_arrows(round_arrows)
        distance = distance_for_round(entry.user_metadata, event.event_id, round_index)
        normalized = _normalized_score(score, len(round_arrows))
        point = ScorePoint(
            date=date,
            tournament_name=t_name,
            event_name=event.event_name,
            division=division_name,
            score=float(score),
            distance=distance,
            normalized=normalized,
            round_index=round_index,
        )
        analytics.normalized_scores.append(point)
        analytics.scores_by_distance.setdefault(distance, []).append(point)
        _append_consistency(
            analytics, date, t_name, event.event_name, round_arrows, arrows_per_end
        )


def _process_custom_points(
    analytics: ArcherAnalytics,
    event: EventResult,
    division_name: str,
    archer: ArcherResult,
    date: str,
    t_name: str,
) -> None:
    from app.services.custom_points import (
        CUSTOM_POINTS_MEDAL_MAX_RANK,
        is_award_custom_points_event,
        is_medal_custom_points_event,
    )

    if event.event_type != "CustomPointsEvent" or archer.rank is None:
        return
    if is_award_custom_points_event(event.event_name):
        return
    if not is_medal_custom_points_event(event.event_name):
        return
    if archer.rank > CUSTOM_POINTS_MEDAL_MAX_RANK:
        return
    points_val = float(archer.points) if archer.points is not None else float(archer.rank)
    analytics.normalized_scores.append(
        ScorePoint(
            date=date,
            tournament_name=t_name,
            event_name=event.event_name,
            division=division_name,
            score=float(archer.rank),
            distance="Team event",
            normalized=0.0,
            round_index=0,
        )
    )
    analytics.scores_by_distance.setdefault("Team event", []).append(
        ScorePoint(
            date=date,
            tournament_name=t_name,
            event_name=event.event_name,
            division=division_name,
            score=points_val,
            distance="Team event",
            normalized=0.0,
            round_index=0,
        )
    )


def _process_matches(
    analytics: ArcherAnalytics,
    archer: ArcherResult,
    date: str,
    t_name: str,
    event_name: str,
    elim_buckets: dict,
) -> None:
    for match in archer.matches:
        side = _archer_side_in_match(archer.name, match)
        if not side:
            continue
        opp = _opponent_side(side, match)
        bucket_key = (event_name, match.round_index)
        if bucket_key not in elim_buckets:
            elim_buckets[bucket_key] = {
                "round_name": match.round_name,
                "event_name": event_name,
                "tournament_name": t_name,
                "wins": 0,
                "losses": 0,
                "arrow_totals": [],
                "vs_higher_wins": 0,
                "vs_higher_total": 0,
                "vs_lower_wins": 0,
                "vs_lower_total": 0,
            }
        bucket = elim_buckets[bucket_key]
        if side.won:
            bucket["wins"] += 1
        else:
            bucket["losses"] += 1
        if side.arrow_string:
            bucket["arrow_totals"].append(scoring.calculate_arrows(side.arrow_string))
        my_rank = side.rank
        opp_rank = opp.rank if opp else None
        if my_rank is not None and opp_rank is not None:
            if opp_rank < my_rank:
                bucket["vs_higher_total"] += 1
                if side.won:
                    bucket["vs_higher_wins"] += 1
            elif opp_rank > my_rank:
                bucket["vs_lower_total"] += 1
                if side.won:
                    bucket["vs_lower_wins"] += 1


def analytics_has_data(analytics: ArcherAnalytics) -> bool:
    return bool(
        analytics.scores_by_distance
        or analytics.normalized_scores
        or analytics.consistency
        or analytics.elimination
    )


def analytics_to_chart_data(analytics: ArcherAnalytics) -> dict:
    scores_labels: dict[str, list[str]] = {}
    scores_values: dict[str, list[float]] = {}
    for distance, points in analytics.scores_by_distance.items():
        sorted_pts = sorted(points, key=lambda p: p.date)
        scores_labels[distance] = [
            f"{p.date} {p.tournament_name[:20]}" for p in sorted_pts
        ]
        scores_values[distance] = [p.score for p in sorted_pts]

    norm_sorted = sorted(analytics.normalized_scores, key=lambda p: p.date)
    elim_labels = [
        f"{e.round_name} ({e.event_name[:12]})" if e.event_name else e.round_name
        for e in analytics.elimination
    ]
    return {
        "scores_by_distance": {
            "labels": scores_labels,
            "values": scores_values,
        },
        "normalized": {
            "labels": [f"{p.date} {p.tournament_name[:20]}" for p in norm_sorted],
            "values": [round(p.normalized * 100, 1) for p in norm_sorted],
        },
        "consistency": {
            "labels": [
                f"{p.date} {p.tournament_name[:12]} {p.event_name[:10]}"
                for p in analytics.consistency
            ],
            "spread": [round(p.end_spread_avg, 2) for p in analytics.consistency],
            "fliers": [round(p.flier_rate * 100, 1) for p in analytics.consistency],
        },
        "elimination": {
            "labels": elim_labels,
            "win_rates": [round(e.win_rate * 100, 1) for e in analytics.elimination],
            "avg_arrows": [round(e.avg_arrows, 1) for e in analytics.elimination],
            "vs_higher": [
                {
                    "wins": e.vs_higher_seed_wins,
                    "total": e.vs_higher_seed_total,
                }
                for e in analytics.elimination
            ],
            "vs_lower": [
                {
                    "wins": e.vs_lower_seed_wins,
                    "total": e.vs_lower_seed_total,
                }
                for e in analytics.elimination
            ],
            "details": [
                {
                    "round_name": e.round_name,
                    "event_name": e.event_name,
                    "tournament_name": e.tournament_name,
                    "wins": e.wins,
                    "losses": e.losses,
                }
                for e in analytics.elimination
            ],
        },
    }
