from app.extensions import db
from app.models import Club, SavedTournament, User
from app.services.snapshot import build_snapshot
from app.services.summary import TournamentSummary


def _login(client, email="coach@example.com"):
    client.post(
        "/auth/register",
        data={
            "email": email,
            "password": "secret123",
            "confirm_password": "secret123",
        },
    )


def _add_club(user_id: int, name: str = "My Club") -> Club:
    club = Club(user_id=user_id, name=name, is_default=True)
    db.session.add(club)
    db.session.commit()
    return club


def _add_saved_entry(user: User, club: Club, **overrides) -> SavedTournament:
    snapshot = build_snapshot(
        overrides.get("tournament_id", 99),
        {
            "tournament_name": overrides.get("tournament_name", "Winter Classic"),
            "location": "Arena",
            "start_date": overrides.get("start_date", "2026-01-10"),
            "end_date": overrides.get("end_date", "2026-01-11"),
        },
        [],
        TournamentSummary(),
    )
    entry = SavedTournament(
        user_id=user.id,
        tournament_id=overrides.get("tournament_id", 99),
        club_id=club.id,
        tournament_name=overrides.get("tournament_name", "Winter Classic"),
        location="Arena",
        start_date=overrides.get("start_date", "2026-01-10"),
        end_date=overrides.get("end_date", "2026-01-11"),
        club_name=club.name,
        snapshot_json=snapshot,
    )
    db.session.add(entry)
    db.session.commit()
    return entry


def test_library_list_sort(client, app):
    _login(client)
    user = User.query.filter_by(email="coach@example.com").first()
    club = _add_club(user.id)
    _add_saved_entry(user, club)

    response = client.get("/library/?sort=name&dir=asc")
    assert response.status_code == 200
    assert b"Winter Classic" in response.data

    response = client.get("/library/?sort=date&dir=desc")
    assert response.status_code == 200
    assert b"2026-01-10" in response.data


def test_library_view(client, app):
    _login(client)
    user = User.query.filter_by(email="coach@example.com").first()
    club = _add_club(user.id, "Archery Club")
    entry = _add_saved_entry(
        user,
        club,
        tournament_id=100,
        tournament_name="Summer Cup",
        start_date=None,
        end_date=None,
    )

    response = client.get(f"/library/{entry.id}")
    assert response.status_code == 200
    assert b"Summer Cup" in response.data
    assert b"Archery Club" in response.data


def test_library_requires_login(client):
    response = client.get("/library/", follow_redirects=False)
    assert response.status_code == 302
