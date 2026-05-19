from app.services.event_parsers import ArcherResult, DivisionResult, EventResult, MatchResult, MatchSide
from app.services.summary import (
    _bracket_medal_for_archer,
    _bracket_round_tier,
    build_summary,
    match_bracket_placement,
)


def _match_event(archers: list[ArcherResult]) -> EventResult:
    return EventResult(
        event_id=1,
        event_name="Elimination",
        event_type="MatchEvent",
        display_order=1,
        divisions=[DivisionResult(name="RM", archers=archers)],
    )


def test_quarter_finals_not_classified_as_semifinal():
    assert _bracket_round_tier("Quarter Finals") == "quarter"
    assert _bracket_round_tier("Semi Finals") == "semi"


def test_quarterfinal_loss_no_bracket_medal():
    """Eliminated in the quarterfinals does not earn a podium medal."""
    archer = ArcherResult(
        name="Dani Gonzalez (5)",
        club="Club",
        rank=5,
        total_score=None,
        matches=[
            MatchResult(
                round_name="1/8th Round",
                round_index=3,
                sides=[
                    MatchSide("Dani Gonzalez (5)", "Club", 5, "A", [], 6, True),
                    MatchSide("Other", "X", 12, "B", [], 2, False),
                ],
            ),
            MatchResult(
                round_name="Quarter Finals",
                round_index=2,
                sides=[
                    MatchSide("Dani Gonzalez (5)", "Club", 5, "A", [], 5, False),
                    MatchSide("Other2", "X", 4, "B", [], 6, True),
                ],
            ),
        ],
    )
    assert _bracket_medal_for_archer(archer) is None
    summary = build_summary([_match_event([archer])])
    assert summary.medals.bronze == 0


def test_semifinal_loss_bronze_match_win_earns_bronze():
    archer = ArcherResult(
        name="Recurve Women Team",
        club="Club",
        rank=1,
        total_score=None,
        matches=[
            MatchResult(
                round_name="Semi Finals",
                round_index=1,
                sides=[
                    MatchSide("Recurve Women Team", "Club", 1, "A", [], 5, False),
                    MatchSide("Top", "X", 1, "B", [], 6, True),
                ],
            ),
            MatchResult(
                round_name="Finals Round",
                round_index=0,
                sides=[
                    MatchSide("Recurve Women Team", "Club", 1, "A", [], 6, True),
                    MatchSide("Bronze Opponent", "X", 2, "B", [], 4, False),
                ],
            ),
        ],
    )
    assert match_bracket_placement(archer) == 3
    assert _bracket_medal_for_archer(archer) == "bronze"
    summary = build_summary([_match_event([archer])])
    assert summary.medals.bronze == 1


def test_semifinal_loss_bronze_match_loss_no_medal():
    archer = ArcherResult(
        name="Recurve Women Team",
        club="Club",
        rank=1,
        total_score=None,
        matches=[
            MatchResult(
                round_name="Semi Finals",
                round_index=1,
                sides=[
                    MatchSide("Recurve Women Team", "Club", 1, "A", [], 5, False),
                    MatchSide("Top", "X", 1, "B", [], 6, True),
                ],
            ),
            MatchResult(
                round_name="Finals Round",
                round_index=0,
                sides=[
                    MatchSide("Recurve Women Team", "Club", 1, "A", [], 4, False),
                    MatchSide("Bronze Opponent", "X", 2, "B", [], 6, True),
                ],
            ),
        ],
    )
    assert match_bracket_placement(archer) == 4
    assert _bracket_medal_for_archer(archer) is None
    summary = build_summary([_match_event([archer])])
    assert summary.medals.bronze == 0


def test_semifinal_loss_earns_bronze():
    archer = ArcherResult(
        name="Dani Gonzalez (5)",
        club="Club",
        rank=5,
        total_score=None,
        matches=[
            MatchResult(
                round_name="1/8th Round",
                round_index=3,
                sides=[
                    MatchSide("Dani Gonzalez (5)", "Club", 5, "A", [], 6, True),
                    MatchSide("Other", "X", 12, "B", [], 2, False),
                ],
            ),
            MatchResult(
                round_name="Quarter Finals",
                round_index=2,
                sides=[
                    MatchSide("Dani Gonzalez (5)", "Club", 5, "A", [], 6, True),
                    MatchSide("Other2", "X", 4, "B", [], 4, False),
                ],
            ),
            MatchResult(
                round_name="Semi Finals",
                round_index=1,
                sides=[
                    MatchSide("Dani Gonzalez (5)", "Club", 5, "A", [], 5, False),
                    MatchSide("Top", "X", 1, "B", [], 6, True),
                ],
            ),
        ],
    )
    assert _bracket_medal_for_archer(archer) == "bronze"
    summary = build_summary([_match_event([archer])])
    assert summary.medals.bronze == 1


def test_ranking_bronze_and_team_gold():
    events = [
        EventResult(
            event_id=1,
            event_name="Qualifying",
            event_type="RankingEvent",
            display_order=1,
            divisions=[
                DivisionResult(
                    name="Women",
                    archers=[
                        ArcherResult("Dani Gonzalez", "Club", 3, total_score=580),
                    ],
                )
            ],
        ),
        EventResult(
            event_id=2,
            event_name="Team Championship",
            event_type="CustomPointsEvent",
            display_order=2,
            divisions=[
                DivisionResult(
                    name="Collegiate",
                    archers=[
                        ArcherResult(
                            "University Team", "Club", 1, total_score=None, points=100.0
                        ),
                    ],
                )
            ],
        ),
    ]
    summary = build_summary(events)
    assert summary.medals.gold == 1
    assert summary.medals.bronze == 1
    assert summary.medals.silver == 0


def test_finals_winner_gets_single_gold():
    archer = ArcherResult(
        name="Alice Smith (1)",
        club="Club",
        rank=1,
        total_score=None,
        matches=[
            MatchResult(
                round_name="Semi Finals",
                round_index=1,
                sides=[
                    MatchSide("Alice Smith (1)", "Club", 1, "A", [], 6, True),
                    MatchSide("B", "X", 2, "B", [], 2, False),
                ],
            ),
            MatchResult(
                round_name="Finals Round",
                round_index=0,
                sides=[
                    MatchSide("Alice Smith (1)", "Club", 1, "A", [], 6, True),
                    MatchSide("C", "X", 3, "B", [], 4, False),
                ],
            ),
        ],
    )
    summary = build_summary([_match_event([archer])])
    assert summary.medals.gold == 1
    assert summary.medals.silver == 0
    assert summary.medals.bronze == 0


def test_combined_ranking_team_and_quarter_loss():
    """Dani-like case: Q3 bronze + team gold + QF elimination = 1 bronze, 1 gold."""
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
            event_name="Team Championship",
            event_type="CustomPointsEvent",
            display_order=2,
            divisions=[
                DivisionResult(
                    name="Collegiate",
                    archers=[
                        ArcherResult(
                            "University Team", "Club", 1, total_score=None, points=100.0
                        ),
                    ],
                )
            ],
        ),
        _match_event(
            [
                ArcherResult(
                    name="Dani Gonzalez (5)",
                    club="Club",
                    rank=5,
                    total_score=None,
                    matches=[
                        MatchResult(
                            round_name="Quarter Finals",
                            round_index=2,
                            sides=[
                                MatchSide("Dani Gonzalez (5)", "Club", 5, "A", [], 5, False),
                                MatchSide("Opp", "X", 1, "B", [], 6, True),
                            ],
                        ),
                    ],
                )
            ]
        ),
    ]
    summary = build_summary(events)
    assert summary.medals.gold == 1
    assert summary.medals.bronze == 1
    assert summary.medals.silver == 0
