import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.balance_board.board import BoardSample
from app.configuration import Settings
from app.main import create_app
from app.models.measurement_session import MeasurementSession, SessionStatus
from app.services.measurement_service import MeasurementService


def test_measurement_crud_date_filters_and_profile_cascade(database):
    engine, profile, url = database
    with Session(engine) as db:
        session = MeasurementSession(profile_id=profile.id, status=SessionStatus.STABILIZING)
        db.add(session)
        db.commit()
        db.refresh(session)
    result = MeasurementService(engine).save_completed_measurement(
        session.id, BoardSample(4, 18.1, 18.1, 18.1, 18.1), 99, 72.4
    )
    with TestClient(create_app(Settings(database_url=url))) as client:
        assert (
            client.get("/api/v1/measurements", params={"profileId": profile.id}).json()[0]["id"]
            == result.id
        )
        assert client.get("/api/v1/measurements", params={"profileId": "other"}).json() == []
        assert (
            client.get("/api/v1/measurements", params={"to": "2000-01-01T00:00:00Z"}).json() == []
        )
        assert len(client.get("/api/v1/measurements", params={"from": "2000-01-01"}).json()) == 1
        response = client.patch(f"/api/v1/measurements/{result.id}", json={"notes": "Al mattino"})
        assert response.json()["notes"] == "Al mattino"
        assert response.json()["weight"] == 72.4
        assert client.delete(f"/api/v1/profiles/{profile.id}").status_code == 204
        assert client.get("/api/v1/measurements").json() == []
        assert client.get(f"/api/v1/sessions/{session.id}").status_code == 404


def test_partial_session_cannot_be_saved(database):
    engine, profile, _ = database
    with Session(engine) as db:
        session = MeasurementSession(profile_id=profile.id)
        db.add(session)
        db.commit()
        db.refresh(session)
    service = MeasurementService(engine)
    with pytest.raises(ValueError, match="stabilizing"):
        service.save_completed_measurement(session.id, BoardSample(0, 18, 18, 18, 18), 100, 72)
    assert service.list_measurements() == []
