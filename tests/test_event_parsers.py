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


def test_ranking_uses_score_standings_not_list_order():
    """Rank is computed from scores across the full division, not ars list position."""
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
    assert result.divisions[0].archers[0].rank == 1


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
