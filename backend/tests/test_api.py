from fastapi.testclient import TestClient

from app.configuration import Settings
from app.main import create_app


def test_profile_crud_camel_case_validation_and_seed(database):
    _, profile, url = database
    with TestClient(create_app(Settings(database_url=url))) as client:
        assert client.get("/api/v1/health").json()["status"] == "ok"
        profiles = client.get("/api/v1/profiles").json()
        assert len(profiles) == 1
        assert profiles[0]["heightCm"] == 180
        assert profiles[0]["createdAt"].endswith("Z")
        assert client.get(f"/api/v1/profiles/{profile.id}").status_code == 200
        invalid = client.post("/api/v1/profiles", json={"name": "   "})
        assert invalid.status_code == 422
        assert "message" in invalid.json()
        created = client.post("/api/v1/profiles", json={"name": "Ada", "heightCm": 170})
        assert created.status_code == 201
        identifier = created.json()["id"]
        updated = client.patch(f"/api/v1/profiles/{identifier}", json={"heightCm": None})
        assert updated.json()["heightCm"] is None
        assert client.delete(f"/api/v1/profiles/{identifier}").status_code == 204
        assert client.get(f"/api/v1/profiles/{identifier}").status_code == 404


def test_websocket_session_cancel_and_conflict(database):
    _, profile, url = database
    with TestClient(create_app(Settings(database_url=url))) as client:
        with client.websocket_connect("/ws/live") as websocket:
            assert websocket.receive_json()["type"] == "board_connected"
            session = client.post("/api/v1/sessions", json={"profileId": profile.id})
            assert session.status_code == 201
            assert websocket.receive_json()["status"] == "WAITING_FOR_USER"
            assert (
                client.post("/api/v1/sessions", json={"profileId": profile.id}).status_code == 409
            )
            assert client.get("/api/v1/sessions/active").json()["id"] == session.json()["id"]
            assert client.delete(f"/api/v1/profiles/{profile.id}").status_code == 409
            cancelled = client.post(f"/api/v1/sessions/{session.json()['id']}/cancel")
            assert cancelled.json()["status"] == "CANCELLED"
            assert client.get("/api/v1/measurements").json() == []


def test_period_filter_rejects_reversed_range(database):
    _, _, url = database
    with TestClient(create_app(Settings(database_url=url))) as client:
        response = client.get(
            "/api/v1/measurements",
            params={"from": "2026-10-05T00:00:00Z", "to": "2026-10-01T00:00:00Z"},
        )
        assert response.status_code == 422
