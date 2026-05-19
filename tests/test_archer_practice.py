from app.extensions import db
from app.models import SavedArcherPractice, User
from app.services.archer_analytics import build_analytics
from app.services.archer_practice import (
    PracticeValidationError,
    practice_to_score_points,
    validate_rounds,
)


def _user():
    user = User(email="practice@test.com")
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()
    return user


def test_validate_rounds_total_and_arrows(app):
    rounds = validate_rounds(
        [
            {"entry_mode": "total", "total_score": 580},
            {
                "entry_mode": "arrows",
                "arrow_string": "777",
                "arrows_per_end": 3,
            },
        ]
    )
    assert rounds[0]["total_score"] == 580
    assert rounds[1]["total_score"] == 21


def test_validate_rounds_rejects_invalid_arrows(app):
    try:
        validate_rounds([{"entry_mode": "arrows", "arrow_string": "7Q7"}])
        assert False, "expected error"
    except PracticeValidationError as exc:
        assert "invalid" in str(exc).lower()


def test_practice_routes(client, app):
    client.post(
        "/auth/register",
        data={
            "email": "pr@test.com",
            "password": "password123",
            "confirm_password": "password123",
        },
        follow_redirects=True,
    )
    client.post("/my-results/set-mode", data={"mode": "archer"})

    resp = client.post(
        "/my-results/practice",
        data={
            "name": "Tuesday indoor",
            "practice_date": "2024-06-15",
            "round_index_0": "0",
            "distance_0": "18m",
            "conditions_0": "calm",
            "entry_mode_0": "arrows",
            "arrow_string_0": "777101010",
            "arrows_per_end_0": "3",
            "num_ends_0": "2",
            "arrow_0_0_0": "7",
            "arrow_0_0_1": "7",
            "arrow_0_0_2": "7",
            "arrow_0_1_0": "10",
            "arrow_0_1_1": "10",
            "arrow_0_1_2": "1",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Tuesday indoor" in resp.data
    practice = SavedArcherPractice.query.filter_by(name="Tuesday indoor").first()
    assert practice is not None
    assert practice.rounds_json[0]["entry_mode"] == "arrows"
    assert practice.rounds_json[0]["arrow_string"] == "777101010"


def test_build_analytics_practice_toggle(app):
    user = _user()
    practice = SavedArcherPractice(
        user_id=user.id,
        name="Practice A",
        practice_date="2024-01-01",
        include_in_analytics=True,
        rounds_json=[
            {
                "round_index": 0,
                "entry_mode": "arrows",
                "arrow_string": "999",
                "arrows_per_end": 3,
                "distance": "18m",
                "total_score": 27,
            }
        ],
    )
    excluded = SavedArcherPractice(
        user_id=user.id,
        name="Practice B",
        practice_date="2024-02-01",
        include_in_analytics=False,
        rounds_json=[
            {
                "round_index": 0,
                "entry_mode": "total",
                "total_score": 600,
                "distance": "70m",
            }
        ],
    )
    db.session.add_all([practice, excluded])
    db.session.commit()

    with_practice = build_analytics([], practices=[practice, excluded], include_practice=True)
    assert "18m" in with_practice.scores_by_distance
    assert not any(p.tournament_name == "Practice B" for p in with_practice.normalized_scores)

    without = build_analytics([], practices=[practice], include_practice=False)
    assert not without.scores_by_distance
