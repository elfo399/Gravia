import asyncio
import json
import time

import pytest
from fastapi.testclient import TestClient

from app.balance_board.bluez_board import BluezRealBoard
from app.balance_board.board import BoardUnavailableError
from app.configuration import Settings
from app.main import create_app
from app.models.measurement_session import SessionStatus
from app.services.session_service import SessionService
from app.websocket.live_measurements import LiveMeasurements

MAC = "00:24:44:6C:0D:A2"


def status(state, epoch=1, reason=None):
    return {
        "version": 1,
        "mac": MAC,
        "type": "status",
        "epoch": epoch,
        "state": state,
        "reason": reason,
    }


def sample(sequence=1, epoch=1):
    return {
        "version": 1,
        "mac": MAC,
        "type": "sample",
        "epoch": epoch,
        "sequence": sequence,
        "captured_at": time.monotonic(),
        "front_left": 10,
        "front_right": 20,
        "rear_left": 15,
        "rear_right": 25,
    }


async def eventually(predicate):
    async with asyncio.timeout(3):
        while not predicate():
            await asyncio.sleep(0.005)


@pytest.fixture
async def connected_board(tmp_path):
    path = str(tmp_path / "board.sock")
    writers = []

    async def client(reader, writer):
        writers.append(writer)
        try:
            await reader.read()
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_unix_server(client, path=path)
    board = BluezRealBoard(MAC, path)
    events = []

    async def publish(event):
        events.append(event)

    await board.start(publish)
    await eventually(lambda: bool(writers))

    async def send(message):
        writers[-1].write((json.dumps(message) + "\n").encode())
        await writers[-1].drain()
        await asyncio.sleep(0.01)

    try:
        yield board, send, events, writers
    finally:
        await board.shutdown()
        server.close()
        await server.wait_closed()


async def test_waiting_samples_and_repeat_power_cycle(connected_board):
    board, send, events, _ = connected_board
    await send(status("WAITING_FOR_POWER", 0))
    assert board.get_status().state == "WAITING_FOR_POWER"
    assert not board.get_status().connected
    assert board.get_status().last_error is None
    await send(status("CONNECTING"))
    await send(sample())
    assert board.get_status().connected
    stream = board.samples()
    next_sample = asyncio.create_task(anext(stream))
    await asyncio.sleep(0)
    await send(sample(2))
    reading = await next_sample
    assert reading.weight == 70
    assert reading.center_x == pytest.approx(20 / 70)
    assert reading.center_y == pytest.approx(-10 / 70)
    await send(status("DISCONNECTING", reason="USER_POWER_OFF"))
    with pytest.raises(BoardUnavailableError):
        await anext(stream)
    await send(status("WAITING_FOR_POWER", reason="USER_POWER_OFF"))
    await asyncio.sleep(0.05)
    assert not board.get_status().connected
    await send(status("CONNECTING", 2))
    await send(sample(3, 2))
    assert board.get_status().connected
    assert any(event.state == "DISCONNECTING" for event in events)


async def test_agent_loss_and_new_connection_cannot_resume_old_session(connected_board):
    board, send, _, writers = connected_board
    await send(sample())
    stream = board.samples()
    pending = asyncio.create_task(anext(stream))
    await asyncio.sleep(0)
    writers[-1].close()
    await eventually(lambda: not board.get_status().connected)
    with pytest.raises(BoardUnavailableError):
        await pending
    await eventually(lambda: len(writers) == 2)
    await send(sample())
    assert board.get_status().connected


@pytest.mark.parametrize("kind", ["duplicate", "old", "invalid", "other_board"])
async def test_stale_corrupt_or_wrong_board_rejected(connected_board, kind):
    board, send, _, _ = connected_board
    await send(sample())
    packet = sample(2)
    if kind == "duplicate":
        packet["sequence"] = 1
    elif kind == "old":
        packet["captured_at"] -= 10
    elif kind == "invalid":
        packet["front_left"] = -1
    else:
        packet["mac"] = "AA:BB:CC:DD:EE:FF"
    await send(packet)
    await eventually(lambda: not board.get_status().connected)


async def test_active_measurement_power_off_saves_no_partial_measurement(database, connected_board):
    board, send, _, _ = connected_board
    engine, profile, _ = database
    await send(sample())
    service = SessionService(engine, board, Settings(), LiveMeasurements())
    session = await service.start_measurement_session(profile.id)
    await asyncio.sleep(0)
    await send(sample(2))
    await send(status("DISCONNECTING", reason="USER_POWER_OFF"))
    await service.task
    assert service.get_session(session.id).status == SessionStatus.ERROR
    assert service.measurements.list_measurements() == []
    await send(status("WAITING_FOR_POWER", reason="USER_POWER_OFF"))
    assert board.get_status().last_error is None


def test_bluez_selection_board_off_start_and_demo_regression(database, tmp_path):
    _, _, url = database
    with TestClient(
        create_app(
            Settings(
                database_url=url,
                board_mode="real",
                board_mac=MAC,
                board_transport="bluez",
                board_socket=str(tmp_path / "none"),
            )
        )
    ) as client:
        assert isinstance(client.app.state.board.hardware, BluezRealBoard)
        assert client.get("/api/v1/board/status").json()["connected"] is False
        assert client.get("/api/v1/health").status_code == 200
    with TestClient(create_app(Settings(database_url=url, board_transport="bluez"))) as client:
        assert client.get("/api/v1/board/status").json()["mode"] == "demo"
        assert client.get("/api/v1/board/status").json()["connected"] is True
