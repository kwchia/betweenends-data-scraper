from app.services.event_parsers import ArcherIdentity, parse_event
from app.services.event_parsers import ArcherResult, DivisionResult, EventResult
from app.services.summary import build_summary


def test_award_custom_points_do_not_count_as_medals():
    events = [
        EventResult(
            event_id=1,
            event_name="Qualifying",
            event_type="RankingEvent",
            display_order=1,
            divisions=[
                DivisionResult(
                    name="Women",
                    archers=[ArcherResult("Dani Gonzalez", "Club", 3, total_score=580)],
                )
            ],
        ),
        EventResult(
            event_id=2,
            event_name="All-American Team",
            event_type="CustomPointsEvent",
            display_order=2,
            divisions=[
                DivisionResult(
                    name="Block 1",
                    archers=[
                        ArcherResult("Dani Gonzalez", "Club", 3, total_score=None, points=50.0)
                    ],
                )
            ],
        ),
        EventResult(
            event_id=3,
            event_name="All Around Archers of the Year",
            event_type="CustomPointsEvent",
            display_order=3,
            divisions=[
                DivisionResult(
                    name="Block 1",
                    archers=[
                        ArcherResult("Dani Gonzalez", "Club", 3, total_score=None, points=40.0)
                    ],
                )
            ],
        ),
    ]
    summary = build_summary(events)
    assert summary.medals.bronze == 1
    assert summary.medals.gold == 0
    assert len([h for h in summary.highlights if "pts" in h.title]) == 0


def test_overall_team_championship_uses_final_row_only():
    event_data = {
        "id": 6464,
        "event_name": "Overall Team Championship Points",
        "etp": "CustomPointsEvent",
        "archers": {
            "1": {"fname": "Winning Team\n[Dani Gonzalez]", "lname": ""},
            "2": {"fname": "Other Team\n[Someone Else]", "lname": ""},
        },
        "data": [
            [
                {"scores": {"1": {"rank": 5, "points": 10}, "2": {"rank": 8, "points": 5}}},
                {"scores": {"1": {"rank": 3, "points": 20}, "2": {"rank": 2, "points": 15}}},
                {"scores": {"1": {"rank": 1, "points": 100}, "2": {"rank": 2, "points": 90}}},
            ]
        ],
    }
    identity = ArcherIdentity(first_name="Dani", last_name="Gonzalez")
    result = parse_event(
        {
            "id": 6464,
            "event_name": "Overall Team Championship Points",
            "event_type": "CustomPointsEvent",
            "display_order": 2,
        },
        event_data,
        None,
        archer_identity=identity,
    )
    assert len(result.divisions) == 1
    assert result.divisions[0].archers[0].rank == 1
    summary = build_summary([result])
    assert summary.medals.gold == 1
    assert summary.medals.bronze == 0


def test_custom_points_rank_11_no_medal():
    events = [
        EventResult(
            event_id=1,
            event_name="Overall Team Championship Points",
            event_type="CustomPointsEvent",
            display_order=1,
            divisions=[
                DivisionResult(
                    name="Overall",
                    archers=[
                        ArcherResult(
                            "University Team", "Club", 11, total_score=None, points=50.0
                        ),
                    ],
                )
            ],
        ),
    ]
    summary = build_summary(events)
    assert summary.medals.gold == 0
    assert summary.medals.bronze == 0
