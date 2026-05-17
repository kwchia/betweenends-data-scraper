from app.services.club_filter import (
    AliasRule,
    archer_club_from_row,
    extract_team_name,
    matches_club,
)


def test_matches_contains():
    aliases = [AliasRule("UCLA", "contains")]
    assert matches_club("UCLA Archery Club", aliases)


def test_matches_exact():
    aliases = [AliasRule("UCLA Archery", "exact")]
    assert matches_club("UCLA Archery", aliases)
    assert not matches_club("UCLA Archery Club", aliases)


def test_extract_team_name():
    fnm = "Lindsey Wilson College\n[Tanner Boyd & A.J. Shagool]"
    assert extract_team_name(fnm) == "Lindsey Wilson College"


def test_archer_club_from_row_prefers_tm():
    assert archer_club_from_row("My Club", "Other\n[Name]") == "My Club"


def test_matches_uc_school_with_comma():
    aliases = [AliasRule("University of California San Diego", "contains")]
    assert matches_club("University of California, San Diego", aliases)
    assert not matches_club("University of California, Berkeley", aliases)


def test_matches_rejects_short_substrings_of_alias():
    aliases = [AliasRule("University of California San Diego", "contains")]
    assert not matches_club("Al", aliases)
    assert not matches_club("Diego", aliases)
