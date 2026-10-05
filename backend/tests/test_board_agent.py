import importlib.util
from pathlib import Path

import pytest

source = Path(__file__).resolve().parents[2] / "host" / "gravia_board_core.py"
spec = importlib.util.spec_from_file_location("board_agent_core", source)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


def lifecycle():
    events, actions = [], []
    board = core.BoardLifecycle(
        events.append, lambda: actions.append("close"), lambda: actions.append("disconnect")
    )
    return board, events, actions


def test_waiting_and_device_initiated_connection():
    board, events, actions = lifecycle()
    assert board.state == "WAITING_FOR_POWER"
    board.changed(False)
    assert actions == []
    board.changed(True)
    assert events[-1]["state"] == "CONNECTING"
    assert board.sample()
    assert events[-1]["state"] == "CONNECTED"
    assert board.epoch == 1


def test_power_edge_debounce_release_reader_before_disconnect_and_passive_wait():
    board, events, actions = lifecycle()
    board.changed(True)
    board.button(True, 1)  # The initial power-on press can still be held.
    board.sample()
    board.button(True, 2)
    assert actions == []
    board.button(False, 3)
    board.button(True, 4)
    board.button(True, 4.01)
    board.button(False, 4.02)
    board.button(True, 4.03)
    assert actions == ["close", "disconnect"]
    assert not board.sample()
    board.changed(True)  # A delayed property notification must not reopen the reader.
    assert board.state == "DISCONNECTING"
    board.changed(False)
    assert board.state == "WAITING_FOR_POWER"
    assert board.reason == "USER_POWER_OFF"
    for _ in range(10):
        board.changed(False)
        assert not board.sample()
    assert actions.count("disconnect") == 1
    board.changed(True)
    assert board.epoch == 2
    board.button(False, 5)
    assert board.sample()
    assert board.reason is None


def test_unexpected_loss_closes_input_and_waits_for_new_power():
    board, _, actions = lifecycle()
    board.changed(True)
    board.sample()
    board.changed(False)
    assert board.reason == "CONNECTION_LOST"
    assert board.state == "WAITING_FOR_POWER"
    assert actions == ["close"]
    board.changed(True)
    assert board.sample()


def test_kernel_calibration_sensor_mapping_and_identical_packets():
    calibration = core.parse_calibration(":".join(["03e8"] * 4 + ["07d0"] * 4 + ["0bb8"] * 4))
    report = bytes([0x32, 0, 0, 0x07, 0xD0, 0x0B, 0xB8, 0x03, 0xE8, 0x05, 0xDC])
    assert core.decode_report(report, calibration) == {
        "front_left": 0,
        "front_right": 17,
        "rear_left": 8.5,
        "rear_right": 34,
    }
    assert core.decode_report(report, calibration) == core.decode_report(report, calibration)
    assert core.decode_report(bytes([0x20, 0, 0]), calibration) is None
    assert core.decode_report(report[:7], calibration) is None


@pytest.mark.parametrize("text", ["1:2", ":".join(["03e8"] * 12)])
def test_invalid_calibration_rejected(text):
    with pytest.raises(ValueError):
        core.parse_calibration(text)
