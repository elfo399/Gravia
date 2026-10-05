import asyncio
import errno
import threading
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlmodel import Session, select
from wiibalance._direct import DirectBalanceBoard
from wiibalance.config import Weights
from wiibalance.state import BoardState

from app.balance_board import real_board, wiibalance_client
from app.balance_board.board import BoardUnavailableError
from app.balance_board.demo_board import DemoBoard
from app.balance_board.real_board import RealBoard, describe_connection_error, map_board_state
from app.configuration import Settings
from app.main import create_app
from app.models.measurement_session import MeasurementSession, SessionStatus
from app.services.session_service import SessionService
from app.websocket.live_measurements import LiveMeasurements

MAC = "AA:BB:CC:DD:EE:FF"


def board_state(connected=True):
    return BoardState(
        weights=Weights(
            top_left=10,
            top_right=20,
            bottom_left=15,
            bottom_right=25,
            raw_top_left=100,
            raw_top_right=200,
            raw_bottom_left=150,
            raw_bottom_right=250,
        ),
        button=False,
        led=True,
        connected=connected,
        battery_raw=0x7D,
        temperature_raw=0,
        reference_temperature=None,
    )


class FakeClient:
    def __init__(self, _address=None):
        self.closed = False
        self.fail = False
        self.freeze = False
        self.state = board_state()
        self.thread_ids = []

    def read_state(self):
        self.thread_ids.append(threading.get_ident())
        if self.fail:
            raise OSError("Read failed")
        if not self.freeze:
            self.state = replace(self.state, weights=replace(self.state.weights))
        return self.state

    def close(self):
        self.closed = True


async def eventually(predicate):
    async with asyncio.timeout(3):
        while not predicate():
            await asyncio.sleep(0.005)


async def capture_status(_status):
    pass


def test_verified_library_sensor_mapping():
    state = board_state()
    sample = map_board_state(state, 3.2)
    assert (sample.front_left, sample.front_right, sample.rear_left, sample.rear_right) == (
        10,
        20,
        15,
        25,
    )
    assert sample.weight == state.weights.total
    assert (sample.center_x, sample.center_y) == pytest.approx(state.weights.center_of_pressure)
    assert sample.elapsed_seconds == 3.2
    empty = replace(
        state,
        weights=replace(state.weights, top_left=0, top_right=0, bottom_left=0, bottom_right=0),
    )
    assert map_board_state(empty, 0).center_x == 0


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1])
def test_invalid_sensors_rejected(value):
    state = board_state()
    with pytest.raises(BoardUnavailableError):
        map_board_state(replace(state, weights=replace(state.weights, top_left=value)), 0)


@pytest.mark.parametrize("mac", ["bad", "00:11:22:33:44", "00:11:22:33:44:GG"])
def test_configuration_rejects_invalid_mac(mac):
    with pytest.raises(ValidationError, match="GRAVIA_BOARD_MAC"):
        Settings(board_mac=mac)


def test_real_mode_requires_mac_and_normalizes_valid_address():
    with pytest.raises(ValidationError, match="GRAVIA_BOARD_MAC is required"):
        Settings(board_mode="real", board_mac="")
    assert Settings(board_mode="real", board_mac=" aa:bb:cc:dd:ee:ff ").board_mac == MAC
    assert Settings(board_mode="demo", board_mac="").board_mode == "demo"


async def test_persistent_connection_and_io_off_event_loop(monkeypatch):
    client = FakeClient()
    calls = []

    def connect(address):
        calls.append((address, threading.get_ident()))
        return client

    monkeypatch.setattr(real_board, "WiibalanceClient", connect)
    statuses = []

    async def publish(status):
        statuses.append(status)

    board = RealBoard(MAC)
    await board.start(publish)
    try:
        await eventually(lambda: board.get_status().connected)
        iterator = board.samples()
        first = await anext(iterator)
        second = await anext(iterator)
        await iterator.aclose()
        assert first.elapsed_seconds >= 0
        assert second.elapsed_seconds > first.elapsed_seconds
        assert len(calls) == 1 and calls[0][0] == MAC
        assert calls[0][1] != threading.get_ident()
        assert all(thread_id != threading.get_ident() for thread_id in client.thread_ids)
        assert board.get_status().battery == 75
        assert board.get_status().last_sample_at is not None
        assert [status.connected for status in statuses] == [False, True]
        assert not client.closed  # cancelling a session must not close shared hardware
    finally:
        await board.shutdown()
    assert client.closed and board._reader_task.done()


async def test_read_error_disconnect_and_reconnect(monkeypatch):
    clients = [FakeClient(), FakeClient()]
    attempts = []

    def connect(address):
        attempts.append(address)
        return clients[min(len(attempts) - 1, 1)]

    monkeypatch.setattr(real_board, "WiibalanceClient", connect)
    monkeypatch.setattr(real_board, "RECONNECT_DELAYS", (0.02, 0.02, 0.02))
    statuses = []

    async def publish(status):
        statuses.append(status)

    board = RealBoard(MAC)
    await board.start(publish)
    try:
        await eventually(lambda: board.get_status().connected)
        stream = board.samples()
        await anext(stream)
        clients[0].fail = True
        with pytest.raises(BoardUnavailableError):
            await anext(stream)
        await eventually(lambda: len(attempts) == 2 and board.get_status().connected)
        assert clients[0].closed
        assert [status.connected for status in statuses] == [False, True, False, True]
        assert board.get_status().last_error is None
    finally:
        await board.shutdown()
    assert clients[1].closed


async def test_stale_snapshot_cannot_complete_a_measurement(monkeypatch, database):
    client = FakeClient()
    client.freeze = True
    monkeypatch.setattr(real_board, "WiibalanceClient", lambda _: client)
    board = RealBoard(MAC, sample_timeout=0.15)
    await board.start(capture_status)
    try:
        await eventually(lambda: board.get_status().connected)
        service = SessionService(database[0], board, Settings(), LiveMeasurements())
        profile = database[1]
        session = await service.start_measurement_session(profile.id)
        await asyncio.wait_for(service.task, 2)
        assert service.get_session(session.id).status == SessionStatus.ERROR
        assert service.measurements.list_measurements() == []
        assert not board.get_status().connected
        await eventually(lambda: client.closed)
    finally:
        await board.shutdown()


async def test_connection_failures_use_bounded_retry_and_stop_promptly(monkeypatch):
    def unavailable(_):
        raise OSError(errno.ENETDOWN, "Adapter powered off")

    monkeypatch.setattr(real_board, "WiibalanceClient", unavailable)
    board = RealBoard(MAC)
    delays = []

    async def record_wait(seconds):
        delays.append(seconds)
        if len(delays) == 4:
            board._stopping.set()

    monkeypatch.setattr(board, "_wait_or_stop", record_wait)
    await board.start(capture_status)
    await board._reader_task
    assert delays == [2, 5, 10, 10]
    assert not board.get_status().connected
    assert "Adattatore" in board.get_status().last_error
    await board.shutdown()


async def test_blocking_constructor_does_not_block_startup_and_is_cleaned_on_shutdown(monkeypatch):
    entered, release = threading.Event(), threading.Event()
    client = FakeClient()

    def slow_connect(_):
        entered.set()
        assert release.wait(3)
        return client

    monkeypatch.setattr(real_board, "WiibalanceClient", slow_connect)
    board = RealBoard(MAC)
    await asyncio.wait_for(board.start(capture_status), 0.1)
    await eventually(entered.is_set)
    stop = asyncio.create_task(board.shutdown())
    await asyncio.sleep(0.02)
    assert not stop.done()
    release.set()
    await asyncio.wait_for(stop, 1)
    assert client.closed and board._reader_task.done()


async def test_shutdown_releases_a_blocked_read(monkeypatch):
    entered, release = threading.Event(), threading.Event()

    class BlockingClient(FakeClient):
        def read_state(self):
            entered.set()
            assert release.wait(3)
            return super().read_state()

        def close(self):
            super().close()
            release.set()

    client = BlockingClient()
    monkeypatch.setattr(real_board, "WiibalanceClient", lambda _: client)
    board = RealBoard(MAC)
    await board.start(capture_status)
    await eventually(entered.is_set)
    await asyncio.wait_for(board.shutdown(), 1)
    assert client.closed and board._reader_task.done()


def test_offline_real_hardware_keeps_health_and_rejects_session(database, monkeypatch):
    def unavailable(_):
        raise ConnectionError("Board is off")

    monkeypatch.setattr(real_board, "WiibalanceClient", unavailable)
    engine, profile, url = database
    app = create_app(Settings(board_mode="real", board_mac=MAC, database_url=url))
    with TestClient(app) as client:
        assert client.get("/api/v1/health").json()["status"] == "ok"
        response = client.get("/api/v1/board/status").json()
        assert response["mode"] == "real" and response["macAddress"] == MAC
        assert response["connected"] is False
        with client.websocket_connect("/ws/live") as socket:
            assert socket.receive_json()["type"] == "board_disconnected"
        assert client.post("/api/v1/sessions", json={"profileId": profile.id}).status_code == 503
        with Session(engine) as db:
            assert db.exec(select(MeasurementSession)).all() == []


async def test_demo_contract_still_produces_samples():
    board = DemoBoard()
    await board.start(capture_status)
    stream = board.samples()
    sample = await anext(stream)
    assert sample.weight == 0 and board.get_status().connected
    assert board.get_status().last_sample_at is not None
    await stream.aclose()
    await board.shutdown()


async def test_real_adapter_uses_existing_stability_and_persists_only_completed_session(
    monkeypatch, database
):
    client = FakeClient()
    attempts = []

    def connect(address):
        attempts.append(address)
        return client

    monkeypatch.setattr(real_board, "WiibalanceClient", connect)
    board = RealBoard(MAC)
    await board.start(capture_status)
    service = SessionService(database[0], board, Settings(stable_duration=0.15), LiveMeasurements())
    try:
        await eventually(lambda: board.get_status().connected)
        cancelled = await service.start_measurement_session(database[1].id)
        await service.cancel_measurement_session(cancelled.id)
        assert not client.closed
        assert service.measurements.list_measurements() == []
        session = await service.start_measurement_session(database[1].id)
        await asyncio.wait_for(service.task, 3)
        assert service.get_session(session.id).status == SessionStatus.COMPLETED
        measurement = service.measurements.list_measurements()[0]
        assert measurement.weight == 70
        assert measurement.front_left == 10 and measurement.rear_right == 25
        assert measurement.center_x == pytest.approx(20 / 70)
        assert len(attempts) == 1
    finally:
        await service.shutdown()
        await board.shutdown()


def test_direct_api_exclusive_ownership_and_worker_join(tmp_path, monkeypatch):
    monkeypatch.setenv("GRAVIA_BOARD_LOCK_PATH", str(tmp_path / "board.lock"))
    monkeypatch.setattr(wiibalance_client, "read_config", lambda: {"units": "metric"})
    calls = []
    closed = threading.Event()
    worker = threading.Thread(target=lambda: closed.wait(3))
    worker.start()

    class Hardware:
        worker_thread = worker

        def disconnect(self):
            calls.append("disconnect")
            closed.set()

        def read_state(self):
            return board_state()

    def factory(*, address, use_daemon):
        calls.append((address, use_daemon))
        return Hardware()

    monkeypatch.setattr(wiibalance_client, "create_balance_board", factory)
    connection = wiibalance_client.WiibalanceClient(MAC)
    try:
        assert connection.read_state().weights.total == 70
        with pytest.raises(BoardUnavailableError, match="già in uso"):
            wiibalance_client.WiibalanceClient(MAC)
    finally:
        connection.close()
    assert not worker.is_alive()
    assert calls == [(MAC, False), "disconnect"]
    # Lock released after closing; another owner may now connect.
    other = wiibalance_client.WiibalanceClient(MAC)
    other.close()


def test_imperial_library_config_is_rejected_and_lock_released(tmp_path, monkeypatch):
    monkeypatch.setenv("GRAVIA_BOARD_LOCK_PATH", str(tmp_path / "board.lock"))
    monkeypatch.setattr(wiibalance_client, "read_config", lambda: {"units": "imperial"})
    for _ in range(2):
        with pytest.raises(BoardUnavailableError, match="units=metric"):
            wiibalance_client.WiibalanceClient(MAC)


def test_library_partial_constructor_failure_closes_sockets_and_worker(tmp_path, monkeypatch):
    monkeypatch.setenv("GRAVIA_BOARD_LOCK_PATH", str(tmp_path / "board.lock"))
    monkeypatch.setattr(wiibalance_client, "read_config", lambda: {"units": "metric"})
    closed = threading.Event()
    worker = threading.Thread(target=lambda: closed.wait(3))

    def broken_init(self, address):
        self.worker_thread = worker
        worker.start()
        raise OSError("LED command failed after worker startup")

    def disconnect(self):
        closed.set()

    monkeypatch.setattr(DirectBalanceBoard, "__init__", broken_init)
    monkeypatch.setattr(DirectBalanceBoard, "disconnect", disconnect)
    monkeypatch.setattr(
        wiibalance_client,
        "create_balance_board",
        lambda **kwargs: DirectBalanceBoard(kwargs["address"]),
    )
    with pytest.raises(OSError, match="LED command"):
        wiibalance_client.WiibalanceClient(MAC)
    assert closed.is_set() and not worker.is_alive()


@pytest.mark.parametrize(
    "error, text",
    [
        (PermissionError("denied"), "Accesso Bluetooth"),
        (OSError(errno.EAFNOSUPPORT, "unsupported"), "rete host"),
        (TimeoutError(), "Nessun nuovo campione"),
    ],
)
def test_errors_are_readable(error, text):
    assert text in describe_connection_error(error)
