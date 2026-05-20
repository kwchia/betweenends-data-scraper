from app.services import scoring
from app.services.archer_filter import ArcherIdentity, matches_archer
from app.services.event_parsers import parse_event
from app.services.summary import build_summary


def test_matches_archer_on_team_roster():
    identity = ArcherIdentity(first_name="Dani", last_name="Gonzalez")
    raw = {"fname": "State University\n[Dani Gonzalez & Alex Smith]", "lname": ""}
    matched, reason = matches_archer(raw, identity)
    assert matched
    assert reason == "team_roster"


def test_ranking_rank_by_score_for_archer():
    event_data = {
        "id": 1,
        "enm": "Qualifying",
        "etp": "RankingEvent",
        "rds": 1,
        "epr": 12,
        "ape": 6,
        "cgs": [
            {
                "nm": "College Women",
                "ars": [{"aid": 10}, {"aid": 20}, {"aid": 30}],
            }
        ],
        "rps": {
            "10": {"aid": 10, "fnm": "Low", "lnm": "Score", "tm": "A"},
            "20": {"aid": 20, "fnm": "Dani", "lnm": "Gonzalez", "tm": "B"},
            "30": {"aid": 30, "fnm": "Top", "lnm": "Score", "tm": "C"},
        },
    }
    scores = {
        "ars": {
            "10": "5" * 72,
            "20": "9" * 72,
            "30": "X" * 72,
        }
    }
    identity = ArcherIdentity(first_name="Dani", last_name="Gonzalez")
    result = parse_event(
        {"id": 1, "event_name": "Qual", "event_type": "RankingEvent", "display_order": 1},
        event_data,
        scores,
        archer_identity=identity,
    )
    assert len(result.divisions) == 1
    archer = result.divisions[0].archers[0]
    assert archer.rank == 2
    assert archer.total_score == scoring.calculate_arrows("9" * 72)


def test_custom_points_team_gold_medal():
    event_data = {
        "id": 2,
        "event_name": "Team Championship",
        "etp": "CustomPointsEvent",
        "archers": {
            "1": {"fname": "Winning Team\n[Dani Gonzalez]", "lname": ""},
            "2": {"fname": "Other Team\n[Someone Else]", "lname": ""},
        },
        "data": [
            [
                {
                    "nm": "Mixed Team",
                    "scores": {
                        "1": {"rank": 99, "points": 10},
                        "2": {"rank": 99, "points": 5},
                    },
                }
            ]
        ],
    }
    identity = ArcherIdentity(first_name="Dani", last_name="Gonzalez")
    result = parse_event(
        {
            "id": 2,
            "event_name": "Team Championship",
            "event_type": "CustomPointsEvent",
            "display_order": 2,
        },
        event_data,
        None,
        archer_identity=identity,
    )
    assert len(result.divisions) == 1
    team = result.divisions[0].archers[0]
    assert team.rank == 1
    assert "Winning Team" in team.name
    summary = build_summary([result], count_bracket_medals=False)
    assert summary.medals.gold == 1
    assert summary.medals.bronze == 0
