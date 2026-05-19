from app.services.archer_filter import ArcherIdentity
from app.services.event_parsers import parse_event


RANKING_EVENT = {
    "id": 3347,
    "enm": "Qualifying Round",
    "etp": "RankingEvent",
    "rds": 2,
    "epr": 12,
    "ape": 6,
    "srl": 1,
    "cgs": [{"nm": "Open Men", "ars": [{"aid": 1}, {"aid": 2}]}],
    "rps": {
        "1": {"aid": 1, "fnm": "Alice", "lnm": "Smith", "tm": "Club A", "rtl": "580|575"},
        "2": {"aid": 2, "fnm": "Bob", "lnm": "Jones", "tm": "Club B"},
    },
}

RANKING_SCORES = {"ars": {"1": "X" * 144, "2": "9" * 144}}


def test_archer_filter_keeps_only_matching_archer(app):
    identity = ArcherIdentity(first_name="Alice", last_name="Smith")
    result = parse_event(
        {"id": 3347, "event_name": "Qual", "event_type": "RankingEvent", "display_order": 1},
        RANKING_EVENT,
        RANKING_SCORES,
        archer_identity=identity,
    )
    assert len(result.divisions) == 1
    archer = result.divisions[0].archers[0]
    assert archer.name == "Alice Smith"
    assert archer.arrow_string
    assert len(archer.round_arrow_strings) == 2
    assert archer.match_reason == "name"


def test_archer_filter_preserves_arrow_string(app):
    identity = ArcherIdentity(first_name="Alice", last_name="Smith")
    result = parse_event(
        {"id": 1, "event_name": "Q", "event_type": "RankingEvent", "display_order": 1},
        RANKING_EVENT,
        RANKING_SCORES,
        archer_identity=identity,
    )
    assert result.divisions[0].archers[0].arrow_string == "X" * 144
