from app.services import scoring


def test_calculate_arrows_indoor():
    assert scoring.calculate_arrows("XTT9") == 39


def test_calculate_arrows_empty():
    assert scoring.calculate_arrows("") == 0
    assert scoring.calculate_arrows(None) == 0


def test_set_score_win():
    assert scoring.get_set_score("XTT", "999", 3) == 2


def test_set_score_tie():
    assert scoring.get_set_score("TTT", "TTT", 3) == 1


def test_get_round_from_match_number_bracket():
    assert scoring.get_round_from_match_number(0, 0, 4) == 0
    assert scoring.get_round_from_match_number(8, 0, 4) == 2


def test_end_score_display_set_format():
    my = "XTT" + "E" * 12
    opp = "999" + "E" * 12
    display = scoring.get_end_score_display(my, opp, 0, 3, 5, 1)
    assert "(" in display
