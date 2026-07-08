from unittest.mock import AsyncMock

SAMPLE_EVENT = {
    "id": 1,
    "name": "Team A vs Team B",
    "description": "Friendly match",
    "coef_1st_team_win": "1.50",
    "coef_2nd_team_win": "2.50",
    "timestamp": "2026-01-01T00:00:00",
    "deadline": "2026-01-02T00:00:00",
    "status": "NOT_FINISHED",
}


async def test_list_available_events(client, monkeypatch):
    monkeypatch.setattr(
        "app.routers.events.rpc_call", AsyncMock(return_value=[SAMPLE_EVENT])
    )

    response = await client.get("/events/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == 1


async def test_list_available_events_upstream_error(client, monkeypatch):
    monkeypatch.setattr(
        "app.routers.events.rpc_call",
        AsyncMock(return_value={"error": "line-provider failure"}),
    )

    response = await client.get("/events/")

    assert response.status_code == 500


async def test_list_available_events_timeout(client, monkeypatch):
    async def _raise(*args, **kwargs):
        raise TimeoutError("no response")

    monkeypatch.setattr("app.routers.events.rpc_call", _raise)

    response = await client.get("/events/")

    assert response.status_code == 504
