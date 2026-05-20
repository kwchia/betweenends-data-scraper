from app.services.event_parsers import ArcherResult, DivisionResult, EventResult, MatchResult, MatchSide
from app.services.summary import (
    build_summary,
    collect_club_roster,
    count_unique_archers,
    is_team_entry,
)


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


def test_individual_roster_lists_athletes_and_categories():
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
                    name="Compound Women",
                    archers=[ArcherResult(name="Bob Jones", club="Club", rank=2, total_score=560)],
                ),
            ],
        ),
        _match_event([ArcherResult(name="Alice Smith (1)", club="Club", rank=1, total_score=None)]),
    ]
    events[1].event_name = "Elimination"
    events[1].divisions[0].name = "Recurve Men"
    summary = build_summary(events)
    assert len(summary.individual_roster) == 2
    alice = next(e for e in summary.individual_roster if e.name == "Alice Smith")
    assert "Recurve Men" in alice.categories
    bob = next(e for e in summary.individual_roster if e.name == "Bob Jones")
    assert bob.categories == ["Compound Women"]


def test_team_roster_from_custom_points():
    events = [
        EventResult(
            event_id=10,
            event_name="Collegiate Target Nationals",
            event_type="CustomPointsEvent",
            display_order=3,
            divisions=[
                DivisionResult(
                    name="Overall",
                    archers=[
                        ArcherResult(
                            name="University of California, San Diego",
                            club="UC San Diego",
                            rank=11,
                            total_score=None,
                            points=150.0,
                        )
                    ],
                )
            ],
        )
    ]
    summary = build_summary(events)
    assert len(summary.team_roster) == 1
    assert summary.team_roster[0].event_name == "Collegiate Target Nationals"
    assert summary.team_roster[0].rank == 11
    assert len(summary.individual_roster) == 0
    assert summary.medals.gold == 0


def test_custom_points_individuals_not_on_team_roster():
    events = [
        EventResult(
            event_id=11,
            event_name="All-American Team",
            event_type="CustomPointsEvent",
            display_order=4,
            divisions=[
                DivisionResult(
                    name="Indoor Nationals",
                    archers=[
                        ArcherResult(
                            name="Alice Smith",
                            club="UC San Diego",
                            rank=5,
                            total_score=None,
                            points=9.5,
                        )
                    ],
                )
            ],
        )
    ]
    summary = build_summary(events)
    assert len(summary.team_roster) == 0
    assert len(summary.individual_roster) == 0


def _bracket_matches(*, won_semi=True, won_final=True, won_bronze=None):
    """Build semi + finals-stage matches for bracket placement tests."""
    semi = MatchResult(
        round_name="Semi Finals",
        round_index=1,
        sides=[
            MatchSide(name="Recurve Women Team", club="My Club", rank=1, target="", end_scores=[], total=6, won=won_semi),
            MatchSide(name="Other Team", club="Other", rank=2, target="", end_scores=[], total=2, won=not won_semi),
        ],
    )
    if won_bronze is not None:
        final = MatchResult(
            round_name="Finals Round",
            round_index=0,
            sides=[
                MatchSide(name="Recurve Women Team", club="My Club", rank=1, target="", end_scores=[], total=6, won=won_bronze),
                MatchSide(name="Bronze Opponent", club="Other", rank=2, target="", end_scores=[], total=4, won=not won_bronze),
            ],
        )
    else:
        final = MatchResult(
            round_name="Finals Round",
            round_index=0,
            sides=[
                MatchSide(name="Recurve Women Team", club="My Club", rank=1, target="", end_scores=[], total=6, won=won_final),
                MatchSide(name="Final Opponent", club="Other", rank=2, target="", end_scores=[], total=4, won=not won_final),
            ],
        )
    return [semi, final]


def test_team_match_gold_when_final_and_semi_won():
    archer = ArcherResult(
        name="Recurve Women Team",
        club="My Club",
        rank=1,
        total_score=None,
        matches=_bracket_matches(won_semi=True, won_final=True),
    )
    assert is_team_entry(archer, "MatchEvent")
    summary = build_summary([_match_event([archer])])
    assert summary.medals.gold == 1
    assert summary.medals.silver == 0
    assert summary.medals.bronze == 0
    assert summary.finishes_by_event["Elimination"]["1st place"] == 1


def test_team_match_silver_when_final_lost():
    archer = ArcherResult(
        name="Recurve Women Team",
        club="My Club",
        rank=1,
        total_score=None,
        matches=_bracket_matches(won_semi=True, won_final=False),
    )
    summary = build_summary([_match_event([archer])])
    assert summary.medals.gold == 0
    assert summary.medals.silver == 1
    assert summary.finishes_by_event["Elimination"]["2nd place"] == 1


def test_team_match_bronze_when_semi_lost_and_bronze_won():
    archer = ArcherResult(
        name="Recurve Women Team",
        club="My Club",
        rank=1,
        total_score=None,
        matches=_bracket_matches(won_semi=False, won_bronze=True),
    )
    summary = build_summary([_match_event([archer])])
    assert summary.medals.bronze == 1
    assert summary.finishes_by_event["Elimination"]["3rd place"] == 1


def test_team_match_fourth_when_bronze_lost():
    archer = ArcherResult(
        name="Recurve Women Team",
        club="My Club",
        rank=1,
        total_score=None,
        matches=_bracket_matches(won_semi=False, won_bronze=False),
    )
    summary = build_summary([_match_event([archer])])
    assert summary.medals.bronze == 0
    assert summary.finishes_by_event["Elimination"]["4th place"] == 1


def test_quarterfinal_loss_does_not_award_medal():
    archer = ArcherResult(
        name="Alice Smith",
        club="My Club",
        rank=1,
        total_score=None,
        matches=[
            MatchResult(
                round_name="Quarter Finals",
                round_index=2,
                sides=[
                    MatchSide(name="Alice Smith", club="My Club", rank=1, target="", end_scores=[], total=5, won=False),
                    MatchSide(name="Top Seed", club="Other", rank=1, target="", end_scores=[], total=6, won=True),
                ],
            )
        ],
    )
    summary = build_summary([_match_event([archer])])
    assert summary.medals.gold == 0
    assert summary.medals.silver == 0
    assert summary.medals.bronze == 0


def test_finishes_grouped_by_event():
    events = [
        _ranking_event([ArcherResult(name="Alice Smith", club="Club", rank=1, total_score=580)]),
        _match_event([ArcherResult(name="Alice Smith", club="Club", rank=1, total_score=None, matches=[])]),
    ]
    events[0].event_name = "Qualification"
    events[1].event_name = "Elimination"
    summary = build_summary(events)
    assert "Qualification" in summary.finishes_by_event
    assert summary.finishes_by_event["Qualification"]["Rank 1"] == 1


def test_ranking_highlights_only_for_top_ten():
    events = [
        _ranking_event(
            [
                ArcherResult(name="Podium Archer", club="Club", rank=3, total_score=600),
                ArcherResult(name="Mid Archer", club="Club", rank=10, total_score=550),
                ArcherResult(name="Outside Archer", club="Club", rank=11, total_score=540),
                ArcherResult(name="Deep Archer", club="Club", rank=32, total_score=500),
            ]
        )
    ]
    summary = build_summary(events)
    titles = {h.title for h in summary.highlights}
    assert "Podium Archer — 3rd" in titles
    assert "Mid Archer — 10th" in titles
    assert "Outside Archer — 11th" not in titles
    assert "Deep Archer — 32nd" not in titles
    assert all(h.kind == "top_finish" for h in summary.highlights if h.kind != "medal")


def test_medal_winners_for_podium_ranks():
    events = [
        _ranking_event(
            [
                ArcherResult(name="Alice Smith", club="Club", rank=1, total_score=580),
                ArcherResult(name="Bob Jones", club="Club", rank=2, total_score=560),
                ArcherResult(name="Carol Lee", club="Club", rank=3, total_score=540),
            ]
        )
    ]
    summary = build_summary(events)
    assert summary.medals.gold == 1
    assert summary.medals.silver == 1
    assert summary.medals.bronze == 1
    assert summary.medals.gold_winners[0].archer_name == "Alice Smith"
    assert summary.medals.silver_winners[0].archer_name == "Bob Jones"
    assert summary.medals.bronze_winners[0].archer_name == "Carol Lee"
    assert summary.medals.gold_winners[0].event_name == "Qualification"


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
