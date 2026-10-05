"""Hardware-independent lifecycle and kernel-compatible Balance Board calibration."""

import struct


def report_button(report):
    # These HID reports carry the two core button bytes before their payload.
    # Extension-only/interleaved reports do not have this layout.
    if len(report) >= 3 and report[0] in (0x20, 0x21, 0x22, *range(0x30, 0x38)):
        return bool(report[2] & 8)
    return None


def parse_calibration(text):
    values = [int(value, 16) for value in text.strip().split(":")]
    if len(values) != 12:
        raise ValueError("Expected twelve Balance Board calibration values")
    points = [values[index : index + 4] for index in (0, 4, 8)]
    if any(not points[0][i] < points[1][i] < points[2][i] for i in range(4)):
        raise ValueError("Invalid Balance Board calibration")
    return points


def decode_report(report, calibration):
    # hidraw includes the report ID, without the L2CAP 0xa1 transport prefix.
    offsets = {0x32: 3, 0x34: 3, 0x35: 6}
    offset = offsets.get(report[0]) if report else None
    if offset is None or len(report) < offset + 8:
        return None
    raw = struct.unpack(">4H", report[offset : offset + 8])
    weights = []
    for i, value in enumerate(raw):
        zero, middle, high = (row[i] for row in calibration)
        if value <= zero:
            grams = 0
        elif value < middle:
            grams = (value - zero) * 1700 // (middle - zero)
        else:
            grams = (value - middle) * 1700 // (high - middle) + 1700
        weights.append(grams / 100)
    return {
        "front_left": weights[2],
        "front_right": weights[0],
        "rear_left": weights[3],
        "rear_right": weights[1],
    }


class BoardLifecycle:
    def __init__(self, publish, close_reader, disconnect):
        self.publish = publish
        self.close_reader = close_reader
        self.disconnect = disconnect
        self.state = "WAITING_FOR_POWER"
        self.reason = None
        self.error = None
        self.device_connected = False
        self.epoch = 0
        self.button_down = None
        self.released_since = None
        self.power_ready_at = None
        self.last_press = float("-inf")

    def snapshot(self):
        return {
            "type": "status",
            "state": self.state,
            "reason": self.reason,
            "error": self.error,
            "epoch": self.epoch,
        }

    def changed(self, connected):
        if connected == self.device_connected:
            return
        self.device_connected = connected
        if connected:
            self.epoch += 1
            self.state = "CONNECTING"
            self.reason = self.error = None
            self.button_down = None
            self.released_since = None
            self.power_ready_at = None
        else:
            self.close_reader()
            if self.reason != "USER_POWER_OFF":
                self.reason = "CONNECTION_LOST"
            self.state = "WAITING_FOR_POWER"
        self.publish(self.snapshot())

    def sample(self, now):
        if (
            self.state == "CONNECTING"
            and self.power_ready_at is not None
            and now >= self.power_ready_at
            and self.button_down is False
            and self.released_since is not None
            and now - self.released_since >= 0.5
        ):
            self.state = "CONNECTED"
            self.error = None
            self.publish(self.snapshot())
        return self.state == "CONNECTED"

    def button(self, pressed, now):
        # On this board the power-on edge can arrive seconds after the first
        # neutral HID reports (up to 6.2 s observed on the Raspberry). Let startup
        # settle, then require a released button before accepting a new press.
        previous, self.button_down = self.button_down, pressed
        if self.power_ready_at is None:
            self.power_ready_at = now + 10
        if not pressed:
            if previous is not False:
                self.released_since = now
            return
        released_since, self.released_since = self.released_since, None
        if (
            pressed
            and previous is False
            and self.state == "CONNECTED"
            and now >= self.power_ready_at
            and released_since is not None
            and now - released_since >= 0.5
            and now - self.last_press >= 0.5
        ):
            self.last_press = now
            self.state = "DISCONNECTING"
            self.reason = "USER_POWER_OFF"
            self.publish(self.snapshot())
            self.close_reader()
            self.disconnect()

    def failed(self, message):
        if self.error != message:
            self.error = message
            self.publish(self.snapshot())

    def reader_failed(self, message):
        self.close_reader()
        previous = self.state
        if self.state != "DISCONNECTING":
            self.state = "CONNECTING" if self.device_connected else "WAITING_FOR_POWER"
        if self.error != message or self.state != previous:
            self.error = message
            self.publish(self.snapshot())
