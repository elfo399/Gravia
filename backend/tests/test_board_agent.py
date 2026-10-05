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


def ready(board, now=0):
    board.button(False, now)
    assert board.sample(now + 10)


def test_waiting_and_device_initiated_connection():
    board, events, actions = lifecycle()
    assert board.state == "WAITING_FOR_POWER"
    board.changed(False)
    assert actions == []
    board.changed(True)
    assert events[-1]["state"] == "CONNECTING"
    board.button(False, 0)
    assert not board.sample(9)
    assert board.sample(10)
    assert events[-1]["state"] == "CONNECTED"
    assert board.epoch == 1


def test_power_edge_debounce_release_reader_before_disconnect_and_passive_wait():
    board, events, actions = lifecycle()
    board.changed(True)
    board.button(True, 1)  # The initial power-on press can still be held.
    assert not board.sample(2)
    board.button(True, 2)
    assert actions == []
    board.button(False, 3)
    assert board.sample(11)
    board.button(True, 12)
    board.button(True, 12.01)
    board.button(False, 12.02)
    board.button(True, 12.03)
    assert actions == ["close", "disconnect"]
    assert not board.sample(13)
    board.changed(True)  # A delayed property notification must not reopen the reader.
    assert board.state == "DISCONNECTING"
    board.changed(False)
    assert board.state == "WAITING_FOR_POWER"
    assert board.reason == "USER_POWER_OFF"
    for _ in range(10):
        board.changed(False)
        assert not board.sample(14)
    assert actions.count("disconnect") == 1
    board.changed(True)
    assert board.epoch == 2
    ready(board, 20)
    assert board.reason is None


def test_unexpected_loss_closes_input_and_waits_for_new_power():
    board, _, actions = lifecycle()
    board.changed(True)
    ready(board)
    board.changed(False)
    assert board.reason == "CONNECTION_LOST"
    assert board.state == "WAITING_FOR_POWER"
    assert actions == ["close"]
    board.changed(True)
    ready(board, 20)


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


@pytest.mark.parametrize("delay", [0.1, 2.64, 6.2, 9.9])
def test_startup_release_grace_does_not_power_off_on_delayed_input_event(delay):
    board, _, actions = lifecycle()
    board.changed(True)
    board.button(False, 10)
    board.button(True, 10 + delay)
    assert actions == []
    board.button(True, 20)  # Holding the startup gesture cannot become an off edge.
    assert not board.sample(20)
    assert actions == []
    board.button(False, 21)
    board.button(True, 21.1)  # Release bounce cannot arm Power.
    assert actions == []
    board.button(False, 22)
    assert board.sample(22.6)
    board.button(True, 23)
    assert actions == ["close", "disconnect"]


def test_power_uses_core_button_reports_even_without_sensor_payload():
    board, _, actions = lifecycle()
    board.changed(True)
    board.button(core.report_button(bytes([0x20, 0, 8])), 1)
    assert not board.sample(1)
    board.button(core.report_button(bytes([0x32, 0, 0])), 2)
    assert actions == []
    assert board.sample(11)
    board.button(core.report_button(bytes([0x30, 0, 8])), 12)
    assert actions == ["close", "disconnect"]
    assert core.report_button(bytes([0x3D, 0, 8])) is None
    assert core.report_button(bytes([0x20, 0])) is None


def test_reader_error_cannot_acknowledge_an_intentional_bluetooth_disconnect():
    board, events, _ = lifecycle()
    board.changed(True)
    ready(board)
    board.button(True, 16)
    board.reader_failed("BlueZ temporarily unavailable")
    assert board.state == "DISCONNECTING"
    assert board.device_connected
    board.changed(True)
    assert board.state == "DISCONNECTING"
    board.changed(False)
    assert events[-1]["state"] == "WAITING_FOR_POWER"


@pytest.mark.parametrize(
    "mac,vendor,expected",
    [
        ("00:24:44:6c:0d:a2", "0005:0000057E:00000306", True),
        ("00:24:44:6c:0d:ff", "0005:0000057E:00000306", False),
        ("00:24:44:6c:0d:a2", "0003:0000057E:00000306", False),
    ],
)
def test_udev_matches_only_target_bluetooth_board_ancestor(tmp_path, mac, vendor, expected):
    path = source.with_name("gravia_board_udev.py")
    spec = importlib.util.spec_from_file_location("udev_match", path)
    matcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(matcher)
    hid = tmp_path / "hid"
    event = hid / "input" / "input7" / "event5"
    event.mkdir(parents=True)
    (event.parent / "uevent").write_text("NAME=Balance Board\n")
    (hid / "uevent").write_text(f"HID_UNIQ={mac}\nHID_ID={vendor}\n")
    assert matcher.matches_board(event, "00:24:44:6C:0D:A2") is expected
