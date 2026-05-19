from app.models import SavedArcherTournament, User
from app.services.archer_analytics import (
    ArcherAnalytics,
    _append_consistency,
    _end_spread,
    analytics_to_chart_data,
    build_analytics,
)
from app.services.archer_practice import practice_to_score_points
from app.services.event_parsers import (
    ArcherResult,
    DivisionResult,
    EventResult,
    MatchResult,
    MatchSide,
)
from app.services.snapshot import build_snapshot
from app.services.summary import build_summary
from app.extensions import db


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
        user_metadata={"events": []},
    )


def test_end_spread_tight_vs_wide():
    assert _end_spread([7, 7, 7]) == 0.0
    assert _end_spread([10, 10, 1]) == 9.0


def test_consistency_from_mixed_ends(app):
    analytics = ArcherAnalytics()
    _append_consistency(
        analytics,
        "2024-01-01",
        "Test",
        "Qual",
        "777101010777777",
        3,
    )
    assert len(analytics.consistency) == 1
    tight = ArcherAnalytics()
    _append_consistency(tight, "2024-01-01", "Test", "Qual", "777777", 3)
    assert analytics.consistency[0].end_spread_avg > tight.consistency[0].end_spread_avg


def test_elimination_per_event_bucket(app):
    user = User(email="elim@test.com")
    user.set_password("x")
    db.session.add(user)
    db.session.commit()

    events = [
        EventResult(
            event_id=1,
            event_name="Open Elim",
            event_type="RankingEvent",
            display_order=1,
            divisions=[
                DivisionResult(
                    name="Open",
                    archers=[
                        ArcherResult(
                            name="Alice Smith",
                            club="Club",
                            rank=4,
                            total_score=0,
                            matches=[
                                MatchResult(
                                    round_name="Quarter Finals",
                                    round_index=2,
                                    sides=[
                                        MatchSide(
                                            name="Alice Smith",
                                            club="Club",
                                            rank=4,
                                            target="A",
                                            end_scores=[],
                                            total=0,
                                            won=True,
                                            arrow_string="999",
                                        ),
                                        MatchSide(
                                            name="Opponent",
                                            club="Other",
                                            rank=1,
                                            target="B",
                                            end_scores=[],
                                            total=0,
                                            won=False,
                                        ),
                                    ],
                                ),
                                MatchResult(
                                    round_name="Semi Finals",
                                    round_index=1,
                                    sides=[
                                        MatchSide(
                                            name="Alice Smith",
                                            club="Club",
                                            rank=4,
                                            target="A",
                                            end_scores=[],
                                            total=0,
                                            won=False,
                                        ),
                                        MatchSide(
                                            name="Top Seed",
                                            club="Other",
                                            rank=1,
                                            target="B",
                                            end_scores=[],
                                            total=0,
                                            won=True,
                                        ),
                                    ],
                                ),
                            ],
                        )
                    ],
                )
            ],
        )
    ]
    saved = _make_saved(user.id, 200, events)
    analytics = build_analytics([saved])
    assert len(analytics.elimination) == 2
    qf = next(e for e in analytics.elimination if e.round_name == "Quarter Finals")
    assert qf.wins == 1
    assert qf.vs_higher_seed_wins == 1
    assert qf.vs_higher_seed_total == 1
    chart = analytics_to_chart_data(analytics)
    assert chart["elimination"]["vs_higher"][0]["wins"] == 1


def test_practice_score_points(app):
    from app.models import SavedArcherPractice

    p = SavedArcherPractice(
        user_id=1,
        name="Indoor",
        practice_date="2024-03-01",
        include_in_analytics=True,
        rounds_json=[
            {
                "round_index": 0,
                "entry_mode": "arrows",
                "arrow_string": "XXX",
                "distance": "18m",
                "total_score": 30,
            }
        ],
    )
    points = practice_to_score_points(p)
    assert len(points) == 1
    assert points[0].score == 30.0
