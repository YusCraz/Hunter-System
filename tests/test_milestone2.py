
"""
Automated tests for Hunter System Milestone 2.

All tests use a temporary database.
Your real hunter.db is not modified.
"""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app import database
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """
    Give each test its own isolated SQLite database.
    """

    # Redirect database operations to a temporary file.
    monkeypatch.setattr(
        database,
        "DB_PATH",
        tmp_path / "test_hunter.db"
    )

    # TestClient runs the FastAPI startup handler.
    with TestClient(app) as test_client:
        yield test_client


def test_profile_created(client):
    """A new Hunter should start at Level 1, Rank E."""

    response = client.get("/api/player")

    assert response.status_code == 200

    player = response.json()

    assert player["display_name"] == "Hunter"
    assert player["level"] == 1
    assert player["rank"] == "E"
    assert player["total_xp"] == 0


def test_quest_awards_xp_once(client):
    """A quest must not award XP twice on one day."""

    quests = client.get(
        "/api/quests/today"
    ).json()["quests"]

    quest = quests[0]

    response = client.post(
        "/api/quests/complete",
        json={"quest_id": quest["id"]}
    )

    assert response.status_code == 200
    assert response.json()["xp_earned"] == quest["xp"]

    # Attempting the same quest twice must fail.
    duplicate = client.post(
        "/api/quests/complete",
        json={"quest_id": quest["id"]}
    )

    assert duplicate.status_code == 409

    # Only the original XP should be saved.
    player = client.get("/api/player").json()

    assert player["total_xp"] == quest["xp"]


def test_xp_survives_new_connection(client):
    """Saved XP must be readable from a fresh connection."""

    quest = client.get(
        "/api/quests/today"
    ).json()["quests"][0]

    client.post(
        "/api/quests/complete",
        json={"quest_id": quest["id"]}
    )

    # Read directly using a new SQLite connection.
    with database.get_connection() as connection:
        row = connection.execute("""
            SELECT total_xp
            FROM players
            WHERE id = 1
        """).fetchone()

    assert row["total_xp"] == quest["xp"]


def test_history_records_completion(client):
    """The history API should include completed quests."""

    quest = client.get(
        "/api/quests/today"
    ).json()["quests"][0]

    client.post(
        "/api/quests/complete",
        json={"quest_id": quest["id"]}
    )

    response = client.get("/api/history")

    assert response.status_code == 200

    activities = response.json()["activities"]

    assert len(activities) == 1
    assert activities[0]["quest_id"] == quest["id"]


def test_season_reset_keeps_lifetime_xp(client):
    """
    Ending a season resets seasonal XP,
    but preserves lifetime XP.
    """

    start_day = date(2026, 10, 18)

    # Start season 1.
    database.sync_season(today=start_day)

    # Award 100 XP in the test database.
    database.save_quest_completion(
        quest_id="test_quest",
        xp_reward=100,
        quest_date=start_day.isoformat()
    )

    before = database.get_player_by_id(
        today=start_day
    )

    assert before["total_xp"] == 100
    assert before["season_xp"] == 100

    # Simulate 30 days passing.
    next_season = start_day + timedelta(days=30)

    after = database.get_player_by_id(
        today=next_season
    )

    assert after["season"] == 2
    assert after["total_xp"] == 100
    assert after["season_xp"] == 0
    assert after["rank"] == "E"

    history = database.get_season_history()

    assert len(history) == 1
    assert history[0]["xp_earned"] == 100


def test_arbitrary_xp_endpoint_is_disabled(client):
    """Users must not award arbitrary XP."""

    response = client.post(
        "/hunter/xp",
        json={"amount": 1000}
    )

    assert response.status_code == 404
