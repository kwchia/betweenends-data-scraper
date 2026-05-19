from dataclasses import dataclass, field
from typing import Optional

from app.services import scoring
from app.services.archer_filter import ArcherIdentity, matches_archer
from app.services.club_filter import AliasRule, archer_club_from_row, extract_team_name, matches_club
from app.services.custom_points import (
    is_award_custom_points_event,
    is_medal_custom_points_event,
    overall_standings_rows,
)


@dataclass
class EndScore:
    end_number: int
    display: str


@dataclass
class MatchSide:
    name: str
    club: str
    rank: Optional[int]
    target: str
    end_scores: list[EndScore]
    total: int
    won: bool
    arrow_string: Optional[str] = None


@dataclass
class MatchResult:
    round_name: str
    round_index: int
    sides: list[MatchSide]


@dataclass
class ArcherResult:
    name: str
    club: str
    rank: Optional[int]
    total_score: Optional[int]
    round_scores: list[int] = field(default_factory=list)
    matches: list[MatchResult] = field(default_factory=list)
    points: Optional[float] = None
    aid: Optional[int] = None
    arrow_string: Optional[str] = None
    round_arrow_strings: list[str] = field(default_factory=list)
    match_reason: Optional[str] = None


@dataclass
class DivisionResult:
    name: str
    archers: list[ArcherResult] = field(default_factory=list)
    rounds: list[str] = field(default_factory=list)


@dataclass
class EventResult:
    event_id: int
    event_name: str
    event_type: str
    display_order: int
    divisions: list[DivisionResult] = field(default_factory=list)
    arrows_per_end: Optional[int] = None
    ends_per_round: Optional[int] = None
    num_rounds: Optional[int] = None


def parse_event(
    event_meta: dict,
    event_data: dict,
    scores_data: Optional[dict],
    aliases: Optional[list[AliasRule]] = None,
    archer_identity: Optional[ArcherIdentity] = None,
) -> EventResult:
    aliases = aliases or []
    event_type = event_meta.get("event_type") or event_data.get("etp") or "Unknown"
    event_id = event_meta.get("id") or event_data.get("id", 0)
    event_name = event_meta.get("event_name") or event_data.get("enm", "Event")
    display_order = event_meta.get("display_order", 0)

    if event_type in ("RankingEvent", "CombinedRankingEvent"):
        divisions = _parse_ranking(event_data, scores_data, aliases, archer_identity)
    elif event_type == "MatchEvent":
        divisions = _parse_match(event_data, scores_data, aliases, archer_identity)
    elif event_type == "CustomPointsEvent":
        divisions = _parse_custom_points(event_data, aliases, archer_identity)
    else:
        divisions = []

    ape = event_data.get("ape")
    epr = event_data.get("epr")
    rds = event_data.get("rds")

    return EventResult(
        event_id=event_id,
        event_name=event_name,
        event_type=event_type,
        display_order=display_order,
        divisions=_filter_empty_divisions(divisions),
        arrows_per_end=ape,
        ends_per_round=epr,
        num_rounds=rds,
    )


def _filter_empty_divisions(divisions: list[DivisionResult]) -> list[DivisionResult]:
    return [d for d in divisions if d.archers or any(a.matches for a in d.archers)]


def _row_matches(
    raw: dict,
    aliases: list[AliasRule],
    archer_identity: Optional[ArcherIdentity],
) -> tuple[bool, Optional[str]]:
    if archer_identity:
        return matches_archer(raw, archer_identity)
    club = archer_club_from_row(raw.get("tm"), raw.get("fnm"))
    if matches_club(club, aliases):
        return True, None
    return False, None


def _split_round_arrows(arrows: str, num_rounds: int, arrows_per_round: int) -> list[str]:
    return [
        arrows[r * arrows_per_round : (r + 1) * arrows_per_round]
        for r in range(num_rounds)
    ]


def _ranking_rows_for_division(
    cg: dict,
    archers_map: dict,
    scores_map: dict,
    num_rounds: int,
    arrows_per_round: int,
) -> list[tuple[int, dict, int, str, list[int]]]:
    """All archers in a division with computed total score, sorted best to worst."""
    rows: list[tuple[int, dict, int, str, list[int]]] = []
    for entry in cg.get("ars") or []:
        aid = entry.get("aid")
        if aid is None:
            continue
        archer = archers_map.get(str(aid)) or archers_map.get(aid)
        if not archer:
            continue
        arrows = scores_map.get(str(aid)) or scores_map.get(aid) or ""
        rtl = archer.get("rtl") or ""
        total = _ranking_total(arrows, rtl, num_rounds, arrows_per_round)
        round_scores = [
            scoring.get_final_round_total(arrows, rtl, r, arrows_per_round)
            for r in range(num_rounds)
        ]
        rows.append((int(aid), archer, total, arrows, round_scores))
    rows.sort(key=lambda row: (-row[2], row[0]))
    return rows


def _parse_ranking(
    event_data: dict,
    scores_data: Optional[dict],
    aliases: list[AliasRule],
    archer_identity: Optional[ArcherIdentity],
) -> list[DivisionResult]:
    archers_map = event_data.get("rps") or {}
    scores_map = (scores_data or {}).get("ars") or {}
    num_rounds = event_data.get("rds") or 1
    ape = event_data.get("ape") or 3
    epr = event_data.get("epr") or 1
    arrows_per_round = ape * epr
    store_arrows = archer_identity is not None

    divisions = []
    for cg in event_data.get("cgs") or []:
        if not cg:
            continue
        division_archers = []
        standings = _ranking_rows_for_division(
            cg, archers_map, scores_map, num_rounds, arrows_per_round
        )
        for tournament_rank, (aid, archer, total, arrows, round_scores) in enumerate(
            standings, start=1
        ):
            matched, reason = _row_matches(archer, aliases, archer_identity)
            if not matched:
                continue

            club = archer_club_from_row(archer.get("tm"))
            division_archers.append(
                ArcherResult(
                    name=f"{archer.get('fnm', '')} {archer.get('lnm', '')}".strip(),
                    club=club,
                    rank=tournament_rank,
                    total_score=total,
                    round_scores=round_scores,
                    aid=aid,
                    arrow_string=arrows if store_arrows else None,
                    round_arrow_strings=(
                        _split_round_arrows(arrows, num_rounds, arrows_per_round)
                        if store_arrows
                        else []
                    ),
                    match_reason=reason,
                )
            )

        division_archers.sort(key=lambda a: a.rank or 9999)

        if division_archers:
            divisions.append(DivisionResult(name=cg.get("nm", "Division"), archers=division_archers))

    return divisions


def _ranking_total(arrows: str, rtl: str, num_rounds: int, arrows_per_round: int) -> int:
    if rtl:
        total = 0
        parts = rtl.split("|")
        for i in range(num_rounds):
            if i < len(parts) and parts[i]:
                total += int(parts[i])
            else:
                total += scoring.round_total(arrows, i, arrows_per_round)
        return total
    return scoring.calculate_arrows(arrows)


def _parse_match(
    event_data: dict,
    scores_data: Optional[dict],
    aliases: list[AliasRule],
    archer_identity: Optional[ArcherIdentity],
) -> list[DivisionResult]:
    scores_map = (scores_data or {}).get("ars") or {}
    store_arrows = archer_identity is not None
    divisions = []

    for mg in event_data.get("mgs") or []:
        epm = mg.get("epm") or 5
        ape = mg.get("ape") or 3
        srl = mg.get("srl") or 0
        met = mg.get("met") or 0
        str_val = mg.get("str") or 1
        n_rounds = scoring.num_rounds(met, str_val)
        round_names = [scoring.get_round_name(r, met, str_val) for r in range(n_rounds)]

        mrs = sorted(mg.get("mrs") or [], key=lambda m: m.get("mnm", 0))
        enriched = []
        for j, mr in enumerate(mrs):
            mrid = mr.get("mrid")
            score_entry = scores_map.get(str(mrid)) or scores_map.get(mrid) or {}
            my_arrows = score_entry.get("avs") or "E" * (ape * epm)
            mr = dict(mr)
            mr["my_arrows"] = my_arrows
            mr["round"] = scoring.get_round_from_match_number(mr.get("mnm", 0), met, str_val)
            opponent_idx = j + 1 if j % 2 == 0 else j - 1
            if 0 <= opponent_idx < len(mrs):
                opp_mrid = mrs[opponent_idx].get("mrid")
                opp_entry = scores_map.get(str(opp_mrid)) or scores_map.get(opp_mrid) or {}
                mr["opponent_arrows"] = opp_entry.get("avs") or "E" * (ape * epm)
            else:
                mr["opponent_arrows"] = "E" * (ape * epm)
            enriched.append(mr)

        club_matches: dict[int, list[MatchResult]] = {r: [] for r in range(n_rounds)}
        club_archers: dict[str, ArcherResult] = {}

        for j in range(0, len(enriched), 2):
            pair = enriched[j : j + 2]
            if len(pair) < 2:
                continue
            a, b = pair[0], pair[1]
            for mr, opp in ((a, b), (b, a)):
                matched, reason = _row_matches(mr, aliases, archer_identity)
                if not matched:
                    continue
                club = archer_club_from_row(mr.get("tm"), mr.get("fnm"))
                name = _match_display_name(mr)
                rnd = mr["round"]
                end_scores = [
                    EndScore(
                        end_number=i + 1,
                        display=scoring.get_end_score_display(
                            mr["my_arrows"],
                            opp.get("my_arrows"),
                            i,
                            ape,
                            epm,
                            srl,
                        ),
                    )
                    for i in range(epm)
                ]
                total = scoring.get_match_total(
                    mr["my_arrows"],
                    opp.get("my_arrows"),
                    epm,
                    ape,
                    srl,
                    mr.get("sts", 0),
                )
                side = MatchSide(
                    name=name,
                    club=club,
                    rank=mr.get("rnk"),
                    target=mr.get("tgt") or "",
                    end_scores=end_scores,
                    total=total,
                    won=mr.get("sts") == 1,
                    arrow_string=mr["my_arrows"] if store_arrows else None,
                )
                opp_side = MatchSide(
                    name=_match_display_name(opp),
                    club=archer_club_from_row(opp.get("tm"), opp.get("fnm")),
                    rank=opp.get("rnk"),
                    target=opp.get("tgt") or "",
                    end_scores=[
                        EndScore(
                            end_number=i + 1,
                            display=scoring.get_end_score_display(
                                opp["my_arrows"],
                                mr["my_arrows"],
                                i,
                                ape,
                                epm,
                                srl,
                            ),
                        )
                        for i in range(epm)
                    ],
                    total=scoring.get_match_total(
                        opp["my_arrows"],
                        mr["my_arrows"],
                        epm,
                        ape,
                        srl,
                        opp.get("sts", 0),
                    ),
                    won=opp.get("sts") == 1,
                    arrow_string=opp.get("my_arrows") if store_arrows else None,
                )
                match = MatchResult(
                    round_name=round_names[rnd] if rnd < len(round_names) else f"Round {rnd}",
                    round_index=rnd,
                    sides=[side, opp_side],
                )
                club_matches.setdefault(rnd, []).append(match)
                if name not in club_archers:
                    club_archers[name] = ArcherResult(
                        name=name,
                        club=club,
                        rank=mr.get("rnk"),
                        total_score=None,
                        match_reason=reason,
                    )
                club_archers[name].matches.append(match)

        division_archers = list(club_archers.values())
        if division_archers:
            divisions.append(
                DivisionResult(
                    name=mg.get("nm", "Division"),
                    archers=division_archers,
                    rounds=[round_names[r] for r in sorted(club_matches.keys()) if club_matches[r]],
                )
            )

    return divisions


def _match_display_name(mr: dict) -> str:
    fnm = (mr.get("fnm") or "").strip()
    lnm = (mr.get("lnm") or "").strip()
    if fnm and "\n[" in fnm:
        return fnm.replace("\n", " ")
    if fnm or lnm:
        rank = mr.get("rnk")
        base = f"{fnm} {lnm}".strip()
        return f"{base} ({rank})" if rank else base
    return "--Bye--"


def _parse_custom_points(
    event_data: dict,
    aliases: list[AliasRule],
    archer_identity: Optional[ArcherIdentity],
) -> list[DivisionResult]:
    archers_map = event_data.get("archers") or {}
    divisions: list[DivisionResult] = []
    default_event_name = event_data.get("event_name") or event_data.get("enm") or "Team Points"

    if archer_identity and is_award_custom_points_event(default_event_name):
        return []

    archer_medal_event = archer_identity and is_medal_custom_points_event(default_event_name)

    for block in event_data.get("data") or []:
        block_rows = list(block or [])
        rows_to_parse = (
            overall_standings_rows(block_rows) if archer_medal_event else block_rows
        )
        for row in rows_to_parse:
            scores = row.get("scores") or {}
            if not scores:
                continue
            row_label = row.get("nm") or row.get("name") or row.get("label")
            division_name = row_label or default_event_name
            if archer_medal_event and not row_label:
                division_name = default_event_name

            rank_by_aid = {
                str(aid_key): rank
                for rank, (aid_key, _score_entry) in enumerate(
                    sorted(
                        scores.items(),
                        key=lambda item: (
                            -float(
                                item[1].get("points")
                                if item[1].get("points") is not None
                                else item[1].get("score") or 0
                            ),
                            int(item[0]) if str(item[0]).isdigit() else 0,
                        ),
                    ),
                    start=1,
                )
            }

            division_archers = []
            for aid_key, score_entry in scores.items():
                archer_info = archers_map.get(str(aid_key)) or archers_map.get(aid_key) or {}
                raw = {
                    "fnm": archer_info.get("fname", ""),
                    "lnm": archer_info.get("lname", ""),
                    **archer_info,
                }
                matched, reason = _row_matches(raw, aliases, archer_identity)
                if not matched:
                    continue
                fname = archer_info.get("fname", "")
                lname = archer_info.get("lname", "")
                display_name = extract_team_name(fname) or f"{fname} {lname}".strip() or fname
                club = extract_team_name(fname) or display_name
                team_rank = rank_by_aid.get(str(aid_key)) or score_entry.get("rank")
                division_archers.append(
                    ArcherResult(
                        name=display_name,
                        club=club,
                        rank=int(team_rank) if team_rank is not None else None,
                        total_score=None,
                        points=score_entry.get("points") or score_entry.get("score"),
                        match_reason=reason,
                    )
                )

            if division_archers:
                division_archers.sort(key=lambda a: (a.rank or 9999))
                divisions.append(
                    DivisionResult(name=division_name, archers=division_archers)
                )

    return divisions
