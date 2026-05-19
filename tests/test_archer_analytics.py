from app.models import SavedArcherTournament, User
from app.services.archer_analytics import analytics_to_chart_data, build_analytics
from app.services.event_parsers import ArcherResult, DivisionResult, EventResult
from app.services.snapshot import build_snapshot
from app.services.summary import build_summary


def _make_saved(user_id, tournament_id, events, start_date="2024-06-01"):
    tournament = {
        "tournament_name": f"Tournament {tournament_id}",
        "location": "Test",
        "start_date": start_date,
        "end_date": start_date,
    }
    summary = build_summary(events)
    snapshot = build_snapshot(tournament_id, tournament, events, summary)
    return SavedArcherTournament(
        user_id=user_id,
        tournament_id=tournament_id,
        tournament_name=tournament["tournament_name"],
        start_date=start_date,
        snapshot_json=snapshot,
        user_metadata={
            "events": [
                {
                    "event_id": 1,
                    "rounds": [{"round_index": 0, "distance": "18m", "conditions": ""}],
                    "notes": "",
                }
            ]
        },
    )


def test_build_analytics_scores_by_distance(app):
    events = [
        EventResult(
            event_id=1,
            event_name="Qual",
            event_type="RankingEvent",
            display_order=1,
            arrows_per_end=6,
            ends_per_round=1,
            num_rounds=1,
            divisions=[
                DivisionResult(
                    name="Open",
                    archers=[
                        ArcherResult(
                            name="Alice Smith",
                            club="Club",
                            rank=1,
                            total_score=600,
                            round_scores=[600],
                            arrow_string="X" * 72,
                            round_arrow_strings=["X" * 72],
                        )
                    ],
                )
            ],
        )
    ]
    saved = _make_saved(1, 100, events)
    analytics = build_analytics([saved])
    assert "18m" in analytics.scores_by_distance
    chart = analytics_to_chart_data(analytics)
    assert chart["normalized"]["values"]
