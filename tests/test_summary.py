from app.services.event_parsers import ArcherResult, DivisionResult, EventResult
from app.services.summary import build_summary, collect_club_roster, count_unique_archers


def _ranking_event(archers: list[ArcherResult]) -> EventResult:
    return EventResult(
        event_id=1,
        event_name="Qualification",
        event_type="RankingEvent",
        display_order=1,
        divisions=[DivisionResult(name="RM", archers=archers)],
    )


def _match_event(archers: list[ArcherResult]) -> EventResult:
    return EventResult(
        event_id=2,
        event_name="Elimination",
        event_type="MatchEvent",
        display_order=2,
        divisions=[DivisionResult(name="RM", archers=archers)],
    )


def test_unique_archers_same_person_ranking_and_match():
    events = [
        _ranking_event([ArcherResult(name="Alice Smith", club="Club", rank=1, total_score=580)]),
        _match_event([ArcherResult(name="Alice Smith (1)", club="Club", rank=1, total_score=None)]),
    ]
    assert count_unique_archers(events) == 1
    assert build_summary(events).total_archers == 1


def test_unique_archers_multiple_divisions_same_event():
    events = [
        EventResult(
            event_id=1,
            event_name="Qualification",
            event_type="RankingEvent",
            display_order=1,
            divisions=[
                DivisionResult(
                    name="Recurve Men",
                    archers=[ArcherResult(name="Alice Smith", club="Club", rank=1, total_score=580)],
                ),
                DivisionResult(
                    name="Recurve Mixed",
                    archers=[ArcherResult(name="Alice Smith", club="Club", rank=2, total_score=560)],
                ),
            ],
        )
    ]
    assert count_unique_archers(events) == 1


def test_ranking_highlights_only_top_ten_finishes():
    events = [
        _ranking_event(
            [
                ArcherResult(name="Top Finisher", club="Club", rank=10, total_score=600),
                ArcherResult(name="Just Missed", club="Club", rank=11, total_score=590),
                ArcherResult(name="Mid Pack", club="Club", rank=25, total_score=550),
            ]
        )
    ]
    highlights = build_summary(events).highlights
    assert len(highlights) == 1
    assert highlights[0].title.startswith("Top Finisher")


def test_club_roster_dedupes_individuals_and_skips_team_points():
    events = [
        _ranking_event(
            [
                ArcherResult(name="Alice Smith", club="Club", rank=1, total_score=580),
                ArcherResult(name="Bob Jones", club="Club", rank=5, total_score=560),
            ]
        ),
        EventResult(
            event_id=3,
            event_name="Overall Team Championship Points",
            event_type="CustomPointsEvent",
            display_order=3,
            divisions=[
                DivisionResult(
                    name="Overall",
                    archers=[
                        ArcherResult(
                            name="University of California, San Diego",
                            club="University of California, San Diego",
                            rank=11,
                            total_score=None,
                            points=80.0,
                        )
                    ],
                )
            ],
        ),
        _match_event(
            [
                ArcherResult(
                    name="University of California, San Diego [Alice Smith & Bob Jones]",
                    club="Club",
                    rank=1,
                    total_score=None,
                )
            ]
        ),
    ]
    summary = build_summary(events, club_roster=True)
    assert summary.total_archers == 2
    assert summary.roster == ["Alice Smith", "Bob Jones"]


def test_unique_archers_counts_distinct_people():
    events = [
        _ranking_event(
            [
                ArcherResult(name="Alice Smith", club="Club", rank=1, total_score=580),
                ArcherResult(name="Bob Jones", club="Club", rank=2, total_score=560),
            ]
        )
    ]
    assert count_unique_archers(events) == 2
