from app.services.club_filter import AliasRule
from app.services.event_parsers import parse_event
from app.services.summary import build_summary


RANKING_EVENT = {
    "id": 3347,
    "enm": "Qualifying Round",
    "etp": "RankingEvent",
    "rds": 1,
    "epr": 12,
    "ape": 6,
    "srl": 1,
    "cgs": [
        {
            "nm": "Open Men",
            "ars": [{"aid": 1}, {"aid": 2}],
        }
    ],
    "rps": {
        "1": {
            "aid": 1,
            "fnm": "Alice",
            "lnm": "Smith",
            "tm": "Test Archery Club",
            "rtl": "580",
        },
        "2": {
            "aid": 2,
            "fnm": "Bob",
            "lnm": "Jones",
            "tm": "Other Club",
            "rtl": "550",
        },
    },
}

RANKING_SCORES = {
    "ars": {
        "1": "X" * 72,
        "2": "9" * 72,
    }
}


def test_ranking_filters_by_club():
    aliases = [AliasRule("Test Archery", "contains")]
    result = parse_event(
        {"id": 3347, "event_name": "Qual", "event_type": "RankingEvent", "display_order": 1},
        RANKING_EVENT,
        RANKING_SCORES,
        aliases,
    )
    assert len(result.divisions) == 1
    assert len(result.divisions[0].archers) == 1
    assert result.divisions[0].archers[0].name == "Alice Smith"
    assert result.divisions[0].archers[0].rank == 1


def test_ranking_rank_by_score_not_archer_list_order():
    """Division standing comes from scores; ars list order is not placement."""
    event = {
        **RANKING_EVENT,
        "cgs": [
            {
                "nm": "Open Men",
                "ars": [{"aid": 2}, {"aid": 1}],
            }
        ],
    }
    aliases = [AliasRule("Test Archery", "contains")]
    result = parse_event(
        {"id": 3347, "event_name": "Qual", "event_type": "RankingEvent", "display_order": 1},
        event,
        RANKING_SCORES,
        aliases,
    )
    assert len(result.divisions[0].archers) == 1
    assert result.divisions[0].archers[0].name == "Alice Smith"
    assert result.divisions[0].archers[0].rank == 1


def test_ranking_assigns_tied_scores_same_place():
    from app.services.event_parsers import _assign_competition_ranks, ArcherResult

    archers = [
        ArcherResult(name="First", club="Club", rank=None, total_score=600),
        ArcherResult(name="Tied A", club="Club", rank=None, total_score=590),
        ArcherResult(name="Tied B", club="Club", rank=None, total_score=590),
        ArcherResult(name="Fourth", club="Club", rank=None, total_score=580),
    ]
    _assign_competition_ranks(archers)
    assert [a.rank for a in archers] == [1, 2, 2, 4]


def test_summary_from_ranking():
    aliases = [AliasRule("Test Archery", "contains")]
    result = parse_event(
        {"id": 1, "event_name": "Qual", "event_type": "RankingEvent", "display_order": 1},
        RANKING_EVENT,
        RANKING_SCORES,
        aliases,
    )
    summary = build_summary([result])
    assert summary.medals.gold >= 1
    assert summary.total_archers == 1


def test_custom_points_overall_team_championship_uses_total_points():
    """Component rows each carry rank=1; overall standing is by summed points."""
    aliases = [AliasRule("UC San Diego", "contains")]
    event_data = {
        "id": 99,
        "event_name": "Overall Team Championship Points",
        "etp": "CustomPointsEvent",
        "archers": {
            "1": {"fname": "University of California, San Diego", "lname": "", "tm": "UC San Diego"},
            "2": {"fname": "Texas A&M University", "lname": "", "tm": "Texas A&M"},
        },
        "data": [
            [
                {
                    "column_label": "Recurve Men",
                    "cnd_name": "Overall Team Championship Points",
                    "group": "Individual",
                    "scores": {
                        "1": {"rank": 1, "points": 5.0},
                        "2": {"rank": 1, "points": 50.0},
                    },
                },
                {
                    "column_label": "Recurve Women",
                    "cnd_name": "Overall Team Championship Points",
                    "group": "Individual",
                    "scores": {
                        "1": {"rank": 1, "points": 10.0},
                        "2": {"rank": 1, "points": 100.0},
                    },
                },
                {
                    "column_label": "Compound Men",
                    "cnd_name": "Overall Team Championship Points",
                    "group": "Official",
                    "scores": {
                        "1": {"rank": 1, "points": 4.0},
                        "2": {"rank": 1, "points": 21.0},
                    },
                },
            ]
        ],
    }
    result = parse_event(
        {
            "id": 99,
            "event_name": "Overall Team Championship Points",
            "event_type": "CustomPointsEvent",
            "display_order": 1,
        },
        event_data,
        None,
        aliases,
    )
    assert len(result.divisions) == 1
    assert result.divisions[0].name == "Overall"
    ucsd = result.divisions[0].archers[0]
    assert ucsd.rank == 2
    assert ucsd.points == 19.0


def test_custom_points_single_table_uses_api_rank():
    aliases = [AliasRule("Taylor", "contains")]
    event_data = {
        "id": 100,
        "event_name": "Eagle Team Rankings",
        "etp": "CustomPointsEvent",
        "archers": {
            "1": {"fname": "Taylor's Archery", "lname": ""},
            "2": {"fname": "Other Club", "lname": ""},
        },
        "data": [
            [
                {
                    "column_label": "Points",
                    "scores": {
                        "1": {"rank": 2, "points": 80},
                        "2": {"rank": 1, "points": 100},
                    },
                }
            ]
        ],
    }
    result = parse_event(
        {"id": 100, "event_name": "Eagle Team Rankings", "event_type": "CustomPointsEvent", "display_order": 1},
        event_data,
        None,
        aliases,
    )
    assert len(result.divisions) == 1
    assert result.divisions[0].archers[0].rank == 2
