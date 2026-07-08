from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

FUTURE_DEADLINE = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()


async def test_create_event(client, monkeypatch):
    monkeypatch.setattr("app.crud.send_message", AsyncMock())

    response = await client.post(
        "/events/",
        json={
            "name": "Team A vs Team B",
            "description": "Friendly match",
            "coef_1st_team_win": "1.50",
            "coef_2nd_team_win": "2.50",
            "deadline": FUTURE_DEADLINE,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Team A vs Team B"
    assert data["status"] == "NOT_FINISHED"


async def test_list_events(client, monkeypatch):
    monkeypatch.setattr("app.crud.send_message", AsyncMock())
    await client.post(
        "/events/",
        json={"name": "Event 1", "deadline": FUTURE_DEADLINE},
    )
    await client.post(
        "/events/",
        json={"name": "Event 2", "deadline": FUTURE_DEADLINE},
    )

    response = await client.get("/events/")

    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_update_event_not_found(client, monkeypatch):
    monkeypatch.setattr("app.crud.send_message", AsyncMock())

    response = await client.put("/events/999", json={"status": "FIRST_TEAM_WON"})

    assert response.status_code == 404


async def test_update_event_status_forces_deadline_and_notifies(client, monkeypatch):
    send_message_mock = AsyncMock()
    monkeypatch.setattr("app.crud.send_message", send_message_mock)

    create_response = await client.post(
        "/events/",
        json={"name": "Event 3", "deadline": FUTURE_DEADLINE},
    )
    event_id = create_response.json()["id"]

    update_response = await client.put(
        f"/events/{event_id}", json={"status": "FIRST_TEAM_WON"}
    )

    assert update_response.status_code == 200
    data = update_response.json()
    assert data["status"] == "FIRST_TEAM_WON"
    assert datetime.fromisoformat(data["deadline"]) < datetime.fromisoformat(
        FUTURE_DEADLINE
    ) - timedelta(hours=1)
    send_message_mock.assert_awaited_once()
