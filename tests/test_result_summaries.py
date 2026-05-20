from app.services.event_parsers import ArcherResult, DivisionResult, EventResult, MatchResult, MatchSide
from app.services.result_summaries import summarize_archer, summarize_division, summarize_match


def _match_event(**kwargs) -> EventResult:
    return EventResult(event_id=1, event_name="Elimination", event_type="MatchEvent", display_order=1, **kwargs)


def _ranking_event(**kwargs) -> EventResult:
    return EventResult(
        event_id=2, event_name="Qualifying", event_type="RankingEvent", display_order=1, **kwargs
    )


def test_match_path_gold_medal_winner():
    archer = ArcherResult(
        name="Recurve Women Team",
        club="Test Club",
        rank=None,
        total_score=None,
        matches=[
            MatchResult(
                round_name="Semi Finals",
                round_index=1,
                sides=[
                    MatchSide("Recurve Women Team", "Test", 1, "A", [], 6, True),
                    MatchSide("Other Team", "Other", 2, "B", [], 2, False),
                ],
            ),
            MatchResult(
                round_name="Finals Round",
                round_index=0,
                sides=[
                    MatchSide("Recurve Women Team", "Test", 1, "A", [], 6, True),
                    MatchSide("Final Opponent", "Other", 1, "B", [], 4, False),
                ],
            ),
        ],
    )
    event = _match_event(divisions=[DivisionResult(name="Recurve College Women", archers=[archer])])
    text = summarize_archer(event, archer)
    assert "1st" in text or "gold" in text.lower()


def test_match_path_win_then_loss():
    archer = ArcherResult(
        name="Recurve Men Team",
        club="Test Club",
        rank=None,
        total_score=None,
        matches=[
            MatchResult(
                round_name="1/8th Round",
                round_index=3,
                sides=[
                    MatchSide("Recurve Men Team", "Test", 1, "A", [], 6, True),
                    MatchSide("Other Team", "Other", 2, "B", [], 4, False),
                ],
            ),
            MatchResult(
                round_name="Quarter Finals",
                round_index=2,
                sides=[
                    MatchSide("Recurve Men Team", "Test", 1, "A", [], 5, False),
                    MatchSide("Top Seed", "Other", 1, "B", [], 6, True),
                ],
            ),
        ],
    )
    event = _match_event(divisions=[DivisionResult(name="Recurve Men", archers=[archer])])
    text = summarize_archer(event, archer)
    assert "won" in text.lower()
    assert "quarter" in text.lower()
    assert "eliminated" in text.lower()


def test_match_summary_scores():
    match = MatchResult(
        round_name="Quarter Finals",
        round_index=2,
        sides=[
            MatchSide("Team A", "Club", 1, "A", [], 6, True),
            MatchSide("Team B", "Club", 2, "B", [], 2, False),
        ],
    )
    assert summarize_match(match, "Team A") == "Beat Team B 6–2"
    assert summarize_match(match, "Team B") == "Lost to Team A 2–6"


def test_ranking_division_summary():
    division = DivisionResult(
        name="Open Men",
        archers=[
            ArcherResult("Alice Smith", "Club", 2, 580),
            ArcherResult("Bob Jones", "Club", 5, 540),
        ],
    )
    event = _ranking_event(divisions=[division])
    text = summarize_division(event, division)
    assert "2nd" in text
    assert "Alice" in text
    assert "5th" in text
    assert "Bob" in text


def test_ranking_single_archer():
    archer = ArcherResult("Alice Smith", "Club", 1, 590)
    event = _ranking_event()
    assert "1st" in summarize_archer(event, archer)
    assert "590" in summarize_archer(event, archer)


def test_semifinal_loss_bronze_match_win():
    """Lost semifinals but won the bronze-medal match (Finals Round at index 0)."""
    archer = ArcherResult(
        name="Recurve College Women Team",
        club="Club",
        rank=None,
        total_score=None,
        matches=[
            MatchResult(
                round_name="Quarter Finals",
                round_index=2,
                sides=[
                    MatchSide("Recurve College Women Team", "Club", 1, "A", [], 6, True),
                    MatchSide("Other", "X", 2, "B", [], 4, False),
                ],
            ),
            MatchResult(
                round_name="Semi Finals",
                round_index=1,
                sides=[
                    MatchSide("Recurve College Women Team", "Club", 1, "A", [], 5, False),
                    MatchSide("Top Seed", "X", 1, "B", [], 6, True),
                ],
            ),
            MatchResult(
                round_name="Finals Round",
                round_index=0,
                sides=[
                    MatchSide("Recurve College Women Team", "Club", 1, "A", [], 6, True),
                    MatchSide("Bronze Opponent", "X", 2, "B", [], 4, False),
                ],
            ),
        ],
    )
    event = _match_event(divisions=[DivisionResult(name="Recurve College Women", archers=[archer])])
    text = summarize_archer(event, archer)
    assert "bronze" in text.lower()
    assert "3rd" in text
    assert "eliminated" not in text.lower()
