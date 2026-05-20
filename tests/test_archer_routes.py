from unittest.mock import patch

from app.extensions import db
from app.models import User


def _register_and_login(client, email="archer@test.com"):
    client.post(
        "/auth/register",
        data={
            "email": email,
            "password": "password123",
            "confirm_password": "password123",
        },
        follow_redirects=True,
    )


def test_mode_switch_to_archer(client):
    _register_and_login(client)
    resp = client.post("/my-results/set-mode", data={"mode": "archer"}, follow_redirects=True)
    assert resp.status_code == 200
    assert b"My tournament library" in resp.data


def test_profile_archer_identity(client):
    _register_and_login(client)
    client.post(
        "/profile/archer-identity",
        data={"first_name": "Test", "last_name": "Archer"},
        follow_redirects=True,
    )
    user = User.query.filter_by(email="archer@test.com").first()
    assert user.first_name == "Test"
    assert user.last_name == "Archer"


def test_queue_requires_name(client):
    _register_and_login(client, "scan@test.com")
    client.post("/my-results/set-mode", data={"mode": "archer"})
    resp = client.post(
        "/my-results/queue",
        json={"tournament_id": 123, "tournament_name": "Test Event"},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 400


@patch("app.services.archer_queue.fetch_archer_tournament_results")
def test_queue_add(mock_fetch, client, app):
    from app.services.event_parsers import ArcherResult, DivisionResult, EventResult

    from app.services.summary import build_summary

    events = [
        EventResult(
            event_id=1,
            event_name="Q",
            event_type="RankingEvent",
            display_order=1,
            divisions=[
                DivisionResult(
                    name="Open",
                    archers=[ArcherResult("Alice Smith", "Club", 1, 580)],
                )
            ],
        )
    ]
    mock_fetch.return_value = (
        {"tournament_name": "Test", "start_date": "2024-01-01"},
        events,
        build_summary(events),
    )

    _register_and_login(client, "scan2@test.com")
    user = User.query.filter_by(email="scan2@test.com").first()
    user.first_name = "Alice"
    user.last_name = "Smith"
    db.session.commit()
    client.post("/my-results/set-mode", data={"mode": "archer"})
    resp = client.post(
        "/my-results/queue",
        json={"tournament_id": 999, "tournament_name": "Test Event"},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "completed", data
