from decimal import Decimal
from unittest.mock import AsyncMock


def mock_event_detail(monkeypatch, payload):
    monkeypatch.setattr("app.crud.rpc_call", AsyncMock(return_value=payload))


async def test_place_bet_success(client, monkeypatch):
    mock_event_detail(
        monkeypatch,
        {"id": 1, "coef_1st_team_win": "1.50", "coef_2nd_team_win": "2.10"},
    )

    response = await client.post(
        "/bets/",
        json={"event_id": 1, "bet_prediction": "FIRST_TEAM_WIN", "amount": "100.00"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["event_id"] == 1
    assert Decimal(data["coefficient"]) == Decimal("1.50")
    assert Decimal(data["possible_winning"]) == Decimal("150.00")
    assert data["status"] == "NOT_PLAYED"


async def test_place_bet_uses_prediction_specific_coefficient(client, monkeypatch):
    mock_event_detail(
        monkeypatch,
        {"id": 2, "coef_1st_team_win": "1.20", "coef_2nd_team_win": "3.00"},
    )

    response = await client.post(
        "/bets/",
        json={"event_id": 2, "bet_prediction": "SECOND_TEAM_WIN", "amount": "20.00"},
    )

    assert response.status_code == 201
    data = response.json()
    assert Decimal(data["coefficient"]) == Decimal("3.00")
    assert Decimal(data["possible_winning"]) == Decimal("60.00")


async def test_place_bet_event_not_found(client, monkeypatch):
    mock_event_detail(monkeypatch, {"error": "Event not found or deadline has passed"})

    response = await client.post(
        "/bets/",
        json={"event_id": 999, "bet_prediction": "FIRST_TEAM_WIN", "amount": "50.00"},
    )

    assert response.status_code == 404


async def test_place_bet_upstream_timeout(client, monkeypatch):
    async def _raise(*args, **kwargs):
        raise TimeoutError("no response")

    monkeypatch.setattr("app.crud.rpc_call", _raise)

    response = await client.post(
        "/bets/",
        json={"event_id": 1, "bet_prediction": "FIRST_TEAM_WIN", "amount": "10.00"},
    )

    assert response.status_code == 504


async def test_list_bets(client, monkeypatch):
    mock_event_detail(
        monkeypatch,
        {"id": 3, "coef_1st_team_win": "1.10", "coef_2nd_team_win": "1.90"},
    )
    await client.post(
        "/bets/",
        json={"event_id": 3, "bet_prediction": "FIRST_TEAM_WIN", "amount": "5.00"},
    )

    response = await client.get("/bets/")

    assert response.status_code == 200
    bets = response.json()
    assert len(bets) == 1
    assert bets[0]["event_id"] == 3
