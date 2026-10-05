import asyncio
import time
from dataclasses import replace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlmodel import Session, select

from app.balance_board.board import BoardSample, BoardUnavailableError
from app.balance_board.calibrated_board import CalibratedBoard
from app.configuration import Settings
from app.main import create_app
from app.models.board_calibration import BoardCalibration
from app.models.board_status import BoardStatus
from app.services.board_calibration_service import BoardCalibrationService, CalibrationPolicy
from app.services.session_service import SessionService
from app.websocket.live_measurements import LiveMeasurements

MAC = "00:24:44:6C:0D:A2"
FAST = CalibrationPolicy(window_seconds=0.035, minimum_samples=6, sample_timeout=0.1)


class FakeBoard:
    def __init__(self, *args):
        self.status = BoardStatus(mode="real", connected=True, mac_address=MAC)
        self.values = [(0.1, 0.2, 0.3, 0.4)]
        self.emitted = 0
        self.fail_at = None
        self.publisher = None

    def get_status(self):
        return self.status.model_copy()

    async def start(self, publisher):
        self.publisher = publisher
        await publisher(self.get_status())

    async def shutdown(self):
        pass

    async def samples(self):
        start = time.monotonic()
        index = 0
        while True:
            await asyncio.sleep(0.005)
            self.emitted += 1
            if not self.status.connected or self.fail_at == self.emitted:
                self.status.connected = False
                raise BoardUnavailableError("Disconnected")
            values = self.values[index % len(self.values)]
            index += 1
            yield BoardSample(time.monotonic() - start, *values)


@pytest.fixture
async def calibration(database):
    engine, profile, _ = database
    board = FakeBoard()
    sessions = SessionService(engine, board, Settings(), LiveMeasurements())
    service = BoardCalibrationService(engine, board, sessions, FAST)
    sessions.calibration = service
    yield service, board, sessions, profile
    await service.shutdown()
    await sessions.shutdown()


async def prepare(service, board):
    session = await service.start()
    await service.acquire(session.id, "tare")
    board.values = [(5.1, 5.2, 5.3, 5.4)]
    await service.acquire(session.id, "reference", 20)
    return session.id


async def finish(service, board):
    identifier = await prepare(service, board)
    board.values = [(5.11, 5.21, 5.31, 5.41)]
    result = await service.acquire(identifier, "verify")
    assert result.valid
    return await service.save(identifier)


async def test_tare_averages_many_samples_and_reference_uses_uncorrected_hardware(calibration):
    service, board, _, _ = calibration
    board.values = [(0.1, 0.2, 0.3, 0.4), (0.12, 0.22, 0.32, 0.42)]
    session = await service.start()
    await service.acquire(session.id, "tare")
    assert board.emitted >= FAST.minimum_samples
    assert service.active.offsets[0] == pytest.approx(0.11, abs=0.002)
    assert not service.read().configured
    board.values = [(4.91, 5.01, 5.11, 5.21)]
    reference = await service.acquire(session.id, "reference", 20)
    assert reference.weight_scale == pytest.approx(20 / 19.2, abs=0.001)
    assert reference.measured_weight_after is None  # Not a tautological "verification".
    assert not service.read().configured


async def test_save_requires_independent_valid_verification_and_persists(calibration, database):
    service, board, sessions, _ = calibration
    identifier = await prepare(service, board)
    with pytest.raises(HTTPException, match="Verifica"):
        await service.save(identifier)
    board.values = [(5.11, 5.21, 5.31, 5.41)]
    result = await service.acquire(identifier, "verify")
    assert result.absolute_error == pytest.approx(0.04)
    assert result.percentage_error == pytest.approx(0.2)
    saved = await service.save(identifier)
    assert saved.configured and saved.active_session is None
    recreated = BoardCalibrationService(database[0], board, sessions, FAST)
    assert recreated.read().calibration.weight_scale == pytest.approx(1)
    assert recreated.read().calibration.measured_weight_after == pytest.approx(20.04)


async def test_offsets_scale_clamping_and_center_of_pressure(calibration):
    service, board, _, _ = calibration
    original = BoardSample(2, 0.05, 10.2, 20.3, 30.4)
    assert service.apply(original) is original
    await finish(service, board)
    service.cached.weight_scale = 2
    corrected = service.apply(original)
    assert corrected == BoardSample(2, 0, 20, 40, 60)
    assert corrected.weight == 120
    assert corrected.center_x == pytest.approx(1 / 3)
    assert corrected.center_y == pytest.approx(-2 / 3)
    board.status.mode = "demo"
    assert service.apply(original) is original


async def test_reset_and_unique_update_preserve_other_boards(calibration, database):
    service, board, _, _ = calibration
    await finish(service, board)
    board.values = [(0.1, 0.2, 0.3, 0.4)]
    await finish(service, board)
    with Session(database[0]) as db:
        assert len(db.exec(select(BoardCalibration)).all()) == 1
    other_mac = MAC[:-2] + "FF"
    board.status.mac_address = other_mac
    assert not service.read().configured
    board.status.mac_address = MAC
    assert service.read().configured
    board.status.connected = False  # Reset does not need an active hardware connection.
    assert not (await service.reset()).configured
    assert service.apply(BoardSample(0, 1, 2, 3, 4)).weight == 10


async def test_cache_does_not_query_for_each_sample(calibration):
    service, board, _, _ = calibration
    await finish(service, board)
    queries = []

    def count(*args):
        queries.append(args[2])

    event.listen(service.engine, "before_cursor_execute", count)
    try:
        for _ in range(20):
            service.apply(BoardSample(0, 1, 2, 3, 4))
        assert queries == []
    finally:
        event.remove(service.engine, "before_cursor_execute", count)


@pytest.mark.parametrize("weight", [0, -1, 151, float("nan"), float("inf")])
async def test_invalid_reference_rejected(calibration, weight):
    service, board, _, _ = calibration
    session = await service.start()
    await service.acquire(session.id, "tare")
    with pytest.raises(HTTPException) as error:
        await service.acquire(session.id, "reference", weight)
    assert error.value.status_code == 422
    assert not service.read().configured


@pytest.mark.parametrize(
    "values,message",
    [
        ([(1, 1, 1, 1)], "peso sopra"),
        ([(0, 0, 0, 0), (1, 1, 1, 1)], "stabile"),
    ],
)
async def test_tare_loaded_or_unstable_rejected_without_partial_save(calibration, values, message):
    service, board, _, _ = calibration
    session = await service.start()
    board.values = values
    with pytest.raises(HTTPException, match=message):
        await service.acquire(session.id, "tare")
    assert service.active.result.stage == "TARE"
    assert not service.read().configured


async def test_incompatible_reference_and_unreliable_verification_cannot_save(calibration):
    service, board, _, _ = calibration
    session = await service.start()
    await service.acquire(session.id, "tare")
    board.values = [(1, 1, 1, 1)]
    with pytest.raises(HTTPException, match="compatibile"):
        await service.acquire(session.id, "reference", 20)
    board.values = [(5.1, 5.2, 5.3, 5.4)]
    await service.acquire(session.id, "reference", 20)
    board.values = [(6, 6, 6, 6)]
    result = await service.acquire(session.id, "verify")
    assert not result.valid
    with pytest.raises(HTTPException, match="Verifica"):
        await service.save(session.id)
    assert not service.read().configured


async def test_exclusive_lock_both_directions_and_duplicate_acquisition(calibration):
    service, board, sessions, profile = calibration
    measurement = await sessions.start_measurement_session(profile.id)
    with pytest.raises(HTTPException) as error:
        await service.start()
    assert error.value.status_code == 409
    await sessions.cancel_measurement_session(measurement.id)
    session = await service.start()
    with pytest.raises(HTTPException) as error:
        await sessions.start_measurement_session(profile.id)
    assert error.value.status_code == 409
    acquisition = asyncio.create_task(service.acquire(session.id, "tare"))
    await asyncio.sleep(0.01)
    with pytest.raises(HTTPException, match="Acquisizione"):
        await service.acquire(session.id, "tare")
    with pytest.raises(HTTPException) as error:
        await sessions.start_measurement_session(profile.id)
    assert error.value.status_code == 409
    await acquisition
    await service.cancel(session.id)
    assert not service.is_active and not service.lock.locked()
    assert sessions.measurements.list_measurements() == []


async def test_failed_verification_retry_invalidates_prior_success(calibration):
    service, board, _, _ = calibration
    identifier = await prepare(service, board)
    assert (await service.acquire(identifier, "verify")).valid
    board.values = [(5, 5, 5, 5), (6, 6, 6, 6)]
    with pytest.raises(HTTPException, match="stabile"):
        await service.acquire(identifier, "verify")
    assert service.active.result.valid is None
    with pytest.raises(HTTPException, match="Verifica"):
        await service.save(identifier)
    assert not service.read().configured


@pytest.mark.parametrize("during_read", [False, True])
async def test_disconnect_aborts_and_preserves_prior_calibration(calibration, during_read):
    service, board, _, _ = calibration
    await finish(service, board)
    previous = service.current().calibrated_at
    session = await service.start()
    if during_read:
        board.fail_at = board.emitted + 3
        with pytest.raises(HTTPException) as error:
            await service.acquire(session.id, "tare")
    else:
        board.status.connected = False
        service.on_board_status(board.get_status())
    with pytest.raises(HTTPException) as error:
        await service.save(session.id)
    assert error.value.status_code == 409
    assert not service.is_active and not service.lock.locked()
    assert service.current().calibrated_at == previous


async def test_cancel_during_acquisition_and_expiry_release_board(calibration):
    service, board, _, _ = calibration
    session = await service.start()
    acquisition = asyncio.create_task(service.acquire(session.id, "tare"))
    await asyncio.sleep(0.01)
    await service.cancel(session.id)
    with pytest.raises(HTTPException):
        await acquisition
    assert not service.is_active and not service.lock.locked()
    session = await service.start()
    service.active.expires_at = time.monotonic() - 1
    assert not service.is_active
    with pytest.raises(HTTPException):
        await service.save(session.id)


async def test_offline_demo_and_missing_samples(calibration):
    service, board, _, _ = calibration
    board.status.connected = False
    with pytest.raises(HTTPException) as error:
        await service.start()
    assert error.value.status_code == 503
    board.status.mode = "demo"
    with pytest.raises(HTTPException) as error:
        await service.start()
    assert error.value.status_code == 409
    board.status.mode = "real"
    board.status.connected = True
    service.policy = replace(FAST, minimum_samples=1000)
    session = await service.start()
    with pytest.raises(HTTPException, match="campioni"):
        await service.acquire(session.id, "tare")
    assert not service.is_active and not service.lock.locked()


async def test_disconnect_while_publishing_start_returns_readable_conflict(calibration):
    service, board, _, _ = calibration

    async def publish(status):
        board.status.connected = False
        service.on_board_status(board.get_status())

    service.publish_status = publish
    with pytest.raises(HTTPException) as error:
        await service.start()
    assert error.value.status_code == 409
    assert not service.is_active and not service.lock.locked()


async def test_corrected_board_applies_once_before_measurement(calibration):
    service, board, _, _ = calibration
    await finish(service, board)
    wrapped = CalibratedBoard(board, service)
    async for sample in wrapped.samples():
        assert sample.weight == pytest.approx(20.04)
        break


@pytest.mark.parametrize(
    "transport,factory", [("bluez", "BluezRealBoard"), ("direct", "RealBoard")]
)
def test_rest_commands_validate_inputs_and_never_accept_client_scale(
    database, monkeypatch, transport, factory
):
    monkeypatch.setattr("app.application_lifecycle." + factory, FakeBoard)
    with TestClient(
        create_app(
            Settings(
                database_url=database[2],
                board_mode="real",
                board_transport=transport,
                board_mac=MAC,
            )
        )
    ) as client:
        client.app.state.calibration.policy = FAST
        root = "/api/v1/board/calibration"
        assert client.get(root).json()["configured"] is False
        session = client.post(root + "/session").json()
        identifier = session["id"]
        path = root + "/session/" + identifier
        assert client.post(path + "/tare", json={"offset": 99}).status_code == 422
        assert client.post(path + "/save", json={"weightScale": 99}).status_code == 422
        assert client.post(path + "/tare").json()["stage"] == "REFERENCE"
        assert client.post(path + "/reference", json={"referenceWeight": 0}).status_code == 422
        client.app.state.calibration.hardware.values = [(5.1, 5.2, 5.3, 5.4)]
        assert client.post(path + "/reference", json={"referenceWeight": 20}).status_code == 200
        assert client.post(path + "/verify").json()["valid"] is True
        saved = client.post(path + "/save").json()
        assert saved["configured"] and saved["calibration"]["boardMac"] == MAC
        assert saved["calibration"]["calibratedAt"].endswith("Z")
        assert client.delete(root).json()["configured"] is False
