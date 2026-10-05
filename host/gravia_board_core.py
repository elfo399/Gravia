"""Hardware-independent lifecycle and kernel-compatible Balance Board calibration."""

import struct


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
        self.first_release = None
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
            self.first_release = None
        else:
            self.close_reader()
            if self.reason != "USER_POWER_OFF":
                self.reason = "CONNECTION_LOST"
            self.state = "WAITING_FOR_POWER"
        self.publish(self.snapshot())

    def sample(self):
        if self.state == "CONNECTING":
            self.state = "CONNECTED"
            self.error = None
            self.publish(self.snapshot())
        return self.state == "CONNECTED"

    def button(self, pressed, now):
        # The press that powers the device on must never be interpreted as power-off.
        previous, self.button_down = self.button_down, pressed
        if not pressed and self.first_release is None:
            self.first_release = now
        if (
            pressed
            and previous is False
            and self.state == "CONNECTED"
            and self.first_release is not None
            and now - self.first_release >= 0.5
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
