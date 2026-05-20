from app.services.archer_filter import (
    ArcherIdentity,
    MembershipEntry,
    matches_archer,
    normalize_archer_name,
)


def test_normalize_archer_name_strips_rank():
    assert normalize_archer_name("Alice Smith (3)") == normalize_archer_name("Alice Smith")


def test_matches_primary_name(app):
    identity = ArcherIdentity(first_name="Alice", last_name="Smith")
    matched, reason = matches_archer({"fnm": "Alice", "lnm": "Smith"}, identity)
    assert matched
    assert reason == "name"


def test_matches_alias(app):
    identity = ArcherIdentity(
        first_name="Alice",
        last_name="Smith",
        name_aliases=["A. Smith"],
    )
    matched, reason = matches_archer({"fnm": "A.", "lnm": "Smith"}, identity)
    assert matched
    assert reason == "alias"


def test_no_fuzzy_substring_match(app):
    identity = ArcherIdentity(first_name="Alice", last_name="Smith")
    matched, _ = matches_archer({"fnm": "Alice", "lnm": "Smithson"}, identity)
    assert not matched


def test_matches_membership_field(app):
    identity = ArcherIdentity(
        first_name="Bob",
        last_name="Jones",
        membership_numbers=[MembershipEntry("USA Archery", "12345")],
    )
    matched, reason = matches_archer({"fnm": "Bob", "lnm": "Jones", "mid": "12345"}, identity)
    assert matched
    assert reason == "membership"
