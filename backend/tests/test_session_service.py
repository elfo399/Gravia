import asyncio

import pytest
from fastapi import HTTPException

from app.balance_board.board import BoardSample
from app.balance_board.real_board import RealBoard
from app.configuration import Settings
from app.models.board_status import BoardStatus
from app.models.measurement_session import SessionStatus
from app.services.session_service import SessionService
from app.websocket.live_measurements import LiveMeasurements


class RecordedEvents(LiveMeasurements):
    def __init__(self):
        super().__init__()
        self.events = []

    async def publish(self, event):
        self.events.append(event)
        await super().publish(event)


class StableTestBoard:
    def get_status(self):
        return BoardStatus(mode="demo", connected=True)

    async def samples(self):
        for index in range(80):
            weight = 0 if index == 0 else 45 if index == 1 else 72.4
            yield BoardSample(
                index / 10, weight * 0.26, weight * 0.24, weight * 0.25, weight * 0.25
            )
            await asyncio.sleep(0)


class WaitingTestBoard(StableTestBoard):
    async def samples(self):
        await asyncio.sleep(10)
        yield BoardSample(10, 0, 0, 0, 0)


class NoisyTestBoard(StableTestBoard):
    async def samples(self):
        for index in range(60):
            weight = 72.4 + (index % 2) * 0.5
            yield BoardSample(index / 10, weight / 4, weight / 4, weight / 4, weight / 4)
            await asyncio.sleep(0)


def service_for(database, board, **settings):
    engine, profile, _ = database
    events = RecordedEvents()
    return SessionService(engine, board, Settings(**settings), events), profile, events


async def test_full_session_and_atomic_measurement_save(database):
    service, profile, events = service_for(database, StableTestBoard())
    session = await service.start_measurement_session(profile.id)
    assert session.status == SessionStatus.WAITING_FOR_USER
    await service.task
    statuses = [event["status"] for event in events.events if event["type"] == "session_status"]
    assert statuses == ["WAITING_FOR_USER", "MEASURING", "STABILIZING", "COMPLETED"]
    assert service.get_session(session.id).status == SessionStatus.COMPLETED
    measurements = service.measurements.list_measurements(profile.id)
    assert len(measurements) == 1
    result = measurements[0]
    assert result.weight == pytest.approx(72.4)
    assert result.stability == 100
    assert (
        result.front_left + result.front_right + result.rear_left + result.rear_right
        == pytest.approx(result.weight)
    )
    assert result.center_x == pytest.approx(-0.02)
    assert result.center_y == pytest.approx(0)
    assert events.events[-1]["type"] == "measurement_completed"
    assert events.events[-1]["measurement"]["measuredAt"].endswith("Z")


async def test_cancel_does_not_save_partial_weight(database):
    service, profile, _ = service_for(database, WaitingTestBoard())
    session = await service.start_measurement_session(profile.id)
    result = await service.cancel_measurement_session(session.id)
    assert result.status == SessionStatus.CANCELLED
    assert result.ended_at is not None
    assert service.measurements.list_measurements() == []


async def test_noisy_session_completes_and_saves_once(database):
    service, profile, events = service_for(database, NoisyTestBoard())
    session = await service.start_measurement_session(profile.id)
    await service.task
    assert service.get_session(session.id).status == SessionStatus.COMPLETED
    measurements = service.measurements.list_measurements(profile.id)
    assert len(measurements) == 1
    assert measurements[0].stability >= 95
    assert 72.4 < measurements[0].weight < 72.9
    assert events.events[-1]["type"] == "measurement_completed"


async def test_timeout_applies_even_when_adapter_stops_sending(database):
    service, profile, events = service_for(database, WaitingTestBoard(), session_timeout=0.02)
    session = await service.start_measurement_session(profile.id)
    await service.task
    assert service.get_session(session.id).status == SessionStatus.ERROR
    assert "Tempo scaduto" in events.events[-1]["message"]
    assert service.measurements.list_measurements() == []


async def test_second_session_is_rejected(database):
    service, profile, _ = service_for(database, WaitingTestBoard())
    session = await service.start_measurement_session(profile.id)
    with pytest.raises(HTTPException) as error:
        await service.start_measurement_session(profile.id)
    assert error.value.status_code == 409
    await service.cancel_measurement_session(session.id)


async def test_real_adapter_offline_rejects_before_creating_session(database):
    service, profile, events = service_for(database, RealBoard("AA:BB:CC:DD:EE:FF"))
    with pytest.raises(HTTPException) as error:
        await service.start_measurement_session(profile.id)
    assert error.value.status_code == 503
    assert "non connessa" in error.value.detail
    assert service.get_active_session() is None
    assert service.task is None
    assert events.events == []


async def test_restart_recovers_interrupted_sessions(database):
    service, profile, _ = service_for(database, WaitingTestBoard())
    session = await service.start_measurement_session(profile.id)
    service.task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await service.task
    service.recover_interrupted_sessions()
    assert service.get_active_session() is None
    assert service.get_session(session.id).status == SessionStatus.ERROR
