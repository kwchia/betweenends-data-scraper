from dataclasses import dataclass, field
from typing import Any, Optional

from app.services import scoring
from app.services.club_filter import (
    AliasRule,
    archer_club_from_row,
    extract_team_name,
    matches_club,
    normalize_for_match,
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


def parse_event(
    event_meta: dict,
    event_data: dict,
    scores_data: Optional[dict],
    aliases: list[AliasRule],
) -> EventResult:
    event_type = event_meta.get("event_type") or event_data.get("etp") or "Unknown"
    event_id = event_meta.get("id") or event_data.get("id", 0)
    event_name = event_meta.get("event_name") or event_data.get("enm", "Event")
    display_order = event_meta.get("display_order", 0)

    if event_type in ("RankingEvent", "CombinedRankingEvent"):
        divisions = _parse_ranking(event_data, scores_data, aliases)
    elif event_type == "MatchEvent":
        divisions = _parse_match(event_data, scores_data, aliases)
    elif event_type == "CustomPointsEvent":
        divisions = _parse_custom_points(event_data, aliases)
    else:
        divisions = []

    return EventResult(
        event_id=event_id,
        event_name=event_name,
        event_type=event_type,
        display_order=display_order,
        divisions=_filter_empty_divisions(divisions),
    )


def _filter_empty_divisions(divisions: list[DivisionResult]) -> list[DivisionResult]:
    return [d for d in divisions if d.archers or any(a.matches for a in d.archers)]


def _assign_competition_ranks(archers: list[ArcherResult]) -> None:
    """Assign division standing from scores (ties share the same place)."""
    ordered = sorted(
        archers,
        key=lambda a: (-(a.total_score or 0), a.name.lower()),
    )
    for index, archer in enumerate(ordered):
        if index == 0:
            archer.rank = 1
        elif (archer.total_score or 0) < (ordered[index - 1].total_score or 0):
            archer.rank = index + 1
        else:
            archer.rank = ordered[index - 1].rank


def _parse_ranking(
    event_data: dict,
    scores_data: Optional[dict],
    aliases: list[AliasRule],
) -> list[DivisionResult]:
    archers_map = event_data.get("rps") or {}
    scores_map = (scores_data or {}).get("ars") or {}
    num_rounds = event_data.get("rds") or 1
    ape = event_data.get("ape") or 3
    epr = event_data.get("epr") or 1
    arrows_per_round = ape * epr

    divisions = []
    for cg in event_data.get("cgs") or []:
        if not cg:
            continue
        division_archers: list[ArcherResult] = []
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
            division_archers.append(
                ArcherResult(
                    name=f"{archer.get('fnm', '')} {archer.get('lnm', '')}".strip(),
                    club=archer_club_from_row(archer.get("tm")),
                    rank=None,
                    total_score=total,
                    round_scores=round_scores,
                )
            )

        _assign_competition_ranks(division_archers)
        division_archers = [a for a in division_archers if matches_club(a.club, aliases)]
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
) -> list[DivisionResult]:
    scores_map = (scores_data or {}).get("ars") or {}
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
                club = archer_club_from_row(mr.get("tm"), mr.get("fnm"))
                if not matches_club(club, aliases):
                    continue
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
                )
                match = MatchResult(
                    round_name=round_names[rnd] if rnd < len(round_names) else f"Round {rnd}",
                    round_index=rnd,
                    sides=[side, opp_side],
                )
                club_matches.setdefault(rnd, []).append(match)
                if name not in club_archers:
                    club_archers[name] = ArcherResult(
                        name=name, club=club, rank=mr.get("rnk"), total_score=None
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


def _coerce_rank(rank) -> Optional[int]:
    if rank is None:
        return None
    try:
        return int(rank)
    except (TypeError, ValueError):
        return None


def _custom_points_rows(event_data: dict) -> list[dict]:
    rows: list[dict] = []
    for block in event_data.get("data") or []:
        for row in block or []:
            if row:
                rows.append(row)
    return rows


def _custom_points_event_title(event_data: dict) -> str:
    return event_data.get("enm") or event_data.get("event_name") or "Team Points"


_ORG_NAME_MARKERS = ("University", "College", " Institute", " School", " Team")


def _is_custom_points_team_archer(archer_info: dict, name: str, club: str) -> bool:
    """Organization/team rows use a display name without a separate person last name."""
    if (archer_info.get("lname") or "").strip():
        return False
    fname = (archer_info.get("fname") or "").strip()
    if not fname:
        return False
    if any(marker in fname for marker in _ORG_NAME_MARKERS):
        return True
    if club:
        club_n = normalize_for_match(club)
        name_n = normalize_for_match(name)
        fname_n = normalize_for_match(fname)
        if name_n == club_n or club_n in fname_n or fname_n in club_n:
            return True
    return False


def _custom_points_archer_identity(
    aid_key: Any,
    archers_map: dict,
) -> Optional[tuple[str, str, str]]:
    archer_info = archers_map.get(str(aid_key)) or archers_map.get(aid_key) or {}
    fname = archer_info.get("fname", "")
    lname = archer_info.get("lname", "")
    name = f"{fname} {lname}".strip() or fname
    club = archer_club_from_row(archer_info.get("tm"), fname) or extract_team_name(fname) or name
    if not name:
        return None
    return name, club, normalize_for_match(club)


def _points_from_score_entry(score_entry: dict) -> float:
    points = score_entry.get("points")
    if points is None:
        points = score_entry.get("score")
    return float(points or 0)


def _archer_from_custom_points_row(
    aid_key: Any,
    score_entry: dict,
    archers_map: dict,
    aliases: list[AliasRule],
) -> Optional[ArcherResult]:
    identity = _custom_points_archer_identity(aid_key, archers_map)
    if identity is None:
        return None
    name, club, _club_key = identity
    if not matches_club(club, aliases):
        return None
    rank = _coerce_rank(score_entry.get("rank"))
    return ArcherResult(
        name=name,
        club=club,
        rank=rank,
        total_score=None,
        points=_points_from_score_entry(score_entry),
    )


def _should_aggregate_team_championship(rows: list[dict], archers_map: dict) -> bool:
    """Overall team championships list many component rows; standing is by total points."""
    if len(rows) < 2:
        return False
    cnd_names = {row.get("cnd_name") for row in rows if row.get("cnd_name")}
    if len(cnd_names) != 1:
        return False
    for row in rows:
        scores = row.get("scores") or {}
        if not scores:
            continue
        aid_key = next(iter(scores))
        archer_info = archers_map.get(str(aid_key)) or archers_map.get(aid_key) or {}
        fname = archer_info.get("fname", "")
        lname = archer_info.get("lname", "")
        name = f"{fname} {lname}".strip() or fname
        club = archer_club_from_row(archer_info.get("tm"), fname) or extract_team_name(fname) or name
        return _is_custom_points_team_archer(archer_info, name, club)
    return False


def _parse_aggregated_team_championship(
    event_data: dict,
    rows: list[dict],
    archers_map: dict,
    aliases: list[AliasRule],
) -> list[DivisionResult]:
    totals: dict[str, float] = {}
    meta: dict[str, tuple[str, str]] = {}

    for row in rows:
        for aid_key, score_entry in (row.get("scores") or {}).items():
            identity = _custom_points_archer_identity(aid_key, archers_map)
            if identity is None:
                continue
            name, club, club_key = identity
            totals[club_key] = totals.get(club_key, 0.0) + _points_from_score_entry(score_entry)
            meta[club_key] = (name, club)

    if not totals:
        return []

    ranked = sorted(totals.items(), key=lambda item: (-item[1], meta[item[0]][0].lower()))
    division_archers: list[ArcherResult] = []
    for overall_rank, (club_key, total_points) in enumerate(ranked, start=1):
        name, club = meta[club_key]
        if not matches_club(club, aliases):
            continue
        division_archers.append(
            ArcherResult(
                name=name,
                club=club,
                rank=overall_rank,
                total_score=None,
                points=total_points,
            )
        )

    if not division_archers:
        return []

    return [DivisionResult(name="Overall", archers=division_archers)]


def _parse_custom_points_tables(
    rows: list[dict],
    archers_map: dict,
    aliases: list[AliasRule],
) -> list[DivisionResult]:
    divisions: list[DivisionResult] = []

    for row in rows:
        division_archers: list[ArcherResult] = []
        for aid_key, score_entry in (row.get("scores") or {}).items():
            archer = _archer_from_custom_points_row(aid_key, score_entry, archers_map, aliases)
            if archer is not None:
                division_archers.append(archer)

        if not division_archers:
            continue

        division_archers.sort(key=lambda a: (a.rank or 9999, a.name.lower()))
        division_name = (
            row.get("column_label")
            or row.get("short_label")
            or row.get("cnd_name")
            or "Points"
        )
        divisions.append(DivisionResult(name=division_name, archers=division_archers))

    return divisions


def _parse_custom_points(event_data: dict, aliases: list[AliasRule]) -> list[DivisionResult]:
    archers_map = event_data.get("archers") or {}
    rows = _custom_points_rows(event_data)
    if not rows:
        return []

    if _should_aggregate_team_championship(rows, archers_map):
        return _parse_aggregated_team_championship(event_data, rows, archers_map, aliases)

    divisions = _parse_custom_points_tables(rows, archers_map, aliases)
    if len(divisions) == 1:
        divisions[0].name = _custom_points_event_title(event_data)
    return divisions
