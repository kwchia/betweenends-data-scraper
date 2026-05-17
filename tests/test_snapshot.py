from app.services.event_parsers import ArcherResult, DivisionResult, EventResult
from app.services.snapshot import build_snapshot, load_snapshot
from app.services.summary import TournamentSummary, build_summary


def test_snapshot_roundtrip():
    events = [
        EventResult(
            event_id=1,
            event_name="Recurve",
            event_type="RankingEvent",
            display_order=1,
            divisions=[
                DivisionResult(
                    name="Men",
                    archers=[
                        ArcherResult(
                            name="Alice",
                            club="Test Club",
                            rank=1,
                            total_score=650,
                            round_scores=[320, 330],
                        )
                    ],
                )
            ],
        )
    ]
    summary = build_summary(events)
    tournament = {
        "tournament_name": "Spring Open",
        "location": "City",
        "start_date": "2026-05-01",
        "end_date": "2026-05-02",
    }
    snapshot = build_snapshot(42, tournament, events, summary)
    loaded_tournament, loaded_events, loaded_summary = load_snapshot(snapshot)

    assert loaded_tournament["tournament_name"] == "Spring Open"
    assert len(loaded_events) == 1
    assert loaded_events[0].divisions[0].archers[0].name == "Alice"
    assert loaded_summary.medals.gold >= 1
