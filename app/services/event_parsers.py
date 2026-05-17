from dataclasses import dataclass, field
from typing import Any, Optional

from app.services import scoring
from app.services.club_filter import AliasRule, archer_club_from_row, extract_team_name, matches_club


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
        division_archers = []
        for tournament_rank, entry in enumerate(cg.get("ars") or [], start=1):
            aid = entry.get("aid")
            if aid is None:
                continue
            archer = archers_map.get(str(aid)) or archers_map.get(aid)
            if not archer:
                continue
            club = archer_club_from_row(archer.get("tm"))
            if not matches_club(club, aliases):
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
                    club=club,
                    rank=tournament_rank,
                    total_score=total,
                    round_scores=round_scores,
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


def _parse_custom_points(event_data: dict, aliases: list[AliasRule]) -> list[DivisionResult]:
    archers_map = event_data.get("archers") or {}
    division_archers = []

    for block in event_data.get("data") or []:
        for row in block or []:
            scores = row.get("scores") or {}
            for aid_key, score_entry in scores.items():
                archer_info = archers_map.get(str(aid_key)) or archers_map.get(aid_key) or {}
                fname = archer_info.get("fname", "")
                lname = archer_info.get("lname", "")
                name = f"{fname} {lname}".strip() or fname
                club = extract_team_name(fname) or name
                if not matches_club(club, aliases):
                    continue
                division_archers.append(
                    ArcherResult(
                        name=name,
                        club=club,
                        rank=score_entry.get("rank"),
                        total_score=None,
                        points=score_entry.get("points") or score_entry.get("score"),
                    )
                )

    if division_archers:
        division_archers.sort(key=lambda a: (a.rank or 9999))
        return [
            DivisionResult(
                name=event_data.get("event_name", "Team Points"),
                archers=division_archers,
            )
        ]
    return []
