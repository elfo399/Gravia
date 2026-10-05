"""BlueZ owns Bluetooth; this service never calls Device1.Connect(). Python 3.11+."""

import asyncio
import contextlib
import json
import logging
import os
import re
import signal
import time
from pathlib import Path

import dbus
import evdev
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib
from gravia_board_core import BoardLifecycle, decode_report, parse_calibration

log = logging.getLogger("gravia-board-agent")


class Agent:
    def __init__(self, mac, socket_path):
        self.mac = mac
        self.socket_path = socket_path
        self.clients = set()
        self.input = None
        self.raw_fd = None
        self.calibration = None
        self.last_packet = 0
        self.last_sent = 0
        self.sequence = 0
        self.loop = asyncio.get_running_loop()
        self.stopping = asyncio.Event()
        self.bus = dbus.SystemBus()
        self.path = None
        self.core = BoardLifecycle(self.publish, self.close_reader, self.disconnect)
        self.bus.add_signal_receiver(
            self.properties_changed,
            dbus_interface="org.freedesktop.DBus.Properties",
            signal_name="PropertiesChanged",
            bus_name="org.bluez",
            path_keyword="path",
        )

    def envelope(self, event):
        return {"version": 1, "mac": self.mac, **event}

    def publish(self, event):
        payload = (json.dumps(self.envelope(event), allow_nan=False) + "\n").encode()
        for writer in tuple(self.clients):
            if writer.is_closing() or writer.transport.get_write_buffer_size() > 65536:
                writer.close()
                self.clients.discard(writer)
            else:
                writer.write(payload)
        if event["type"] == "status":
            log.info("Board %s: %s (%s)", self.mac, event["state"], event.get("reason"))

    async def client(self, reader, writer):
        # Read-only protocol. Disconnecting Gravia does not power off the board.
        self.clients.add(writer)
        writer.write((json.dumps(self.envelope(self.core.snapshot())) + "\n").encode())
        try:
            await reader.read(1)
        finally:
            self.clients.discard(writer)
            writer.close()
            with contextlib.suppress(OSError):
                await writer.wait_closed()

    def properties_changed(self, interface, changed, invalidated, path):
        if str(path) == self.path and str(interface) == "org.bluez.Device1":
            if "Connected" in changed:
                self.core.changed(bool(changed["Connected"]))

    def observe_bluez(self):
        # Property observation only, including recovery after bluetooth.service restarts.
        manager = dbus.Interface(
            self.bus.get_object("org.bluez", "/", introspect=False),
            "org.freedesktop.DBus.ObjectManager",
        )
        for path, interfaces in manager.GetManagedObjects(timeout=2).items():
            device = interfaces.get("org.bluez.Device1", {})
            if str(device.get("Address", "")).upper() != self.mac:
                continue
            self.path = str(path)
            self.core.changed(bool(device.get("Connected", False)))
            if not device.get("Paired") or not device.get("Trusted"):
                self.core.failed(
                    "Configurazione iniziale incompleta: associa e autorizza la board."
                )
            elif self.core.error and self.core.error.startswith(
                ("Configurazione iniziale", "Balance Board non associata")
            ):
                self.core.error = None
                self.publish(self.core.snapshot())
            return
        self.path = None
        self.core.changed(False)
        self.core.failed("Balance Board non associata. Esegui la configurazione iniziale.")

    def open_reader(self):
        for raw in Path("/sys/class/hidraw").glob("hidraw*"):
            device = (raw / "device").resolve()
            info = dict(
                line.split("=", 1)
                for line in (device / "uevent").read_text().splitlines()
                if "=" in line
            )
            if info.get("HID_UNIQ", "").upper() != self.mac:
                continue
            calibration_path = device / "bboard_calib"
            if not calibration_path.exists():
                continue  # Wait for hid-wiimote to finish probing, not a generic HID reader.
            for event in device.glob("input/input*/event*"):
                input_device = evdev.InputDevice("/dev/input/" + event.name)
                if "Balance Board" not in input_device.name:
                    input_device.close()
                    continue
                try:
                    calibration = parse_calibration(calibration_path.read_text())
                    fd = os.open("/dev/" + raw.name, os.O_RDONLY | os.O_NONBLOCK)
                except Exception:
                    input_device.close()
                    raise
                self.input, self.raw_fd, self.calibration = input_device, fd, calibration
                self.last_packet = time.monotonic()
                self.loop.add_reader(fd, self.read_raw)
                self.loop.add_reader(input_device.fd, self.read_input)
                log.info("Reader opened for %s; calibration verified", self.mac)
                return

    def close_reader(self):
        if self.input is not None:
            self.loop.remove_reader(self.input.fd)
            self.input.close()
            self.input = None
        if self.raw_fd is not None:
            self.loop.remove_reader(self.raw_fd)
            os.close(self.raw_fd)
            self.raw_fd = None
        self.calibration = None

    def read_input(self):
        try:
            for event in self.input.read():
                if event.type == evdev.ecodes.EV_KEY and event.code == evdev.ecodes.BTN_A:
                    if event.value in (0, 1):
                        self.core.button(bool(event.value), time.monotonic())
                        if self.input is None:
                            return
                elif event.type == evdev.ecodes.EV_SYN and event.code == evdev.ecodes.SYN_DROPPED:
                    self.core.failed("Flusso del pulsante interrotto. Riaccendi la board.")
                    self.close_reader()
                    return
        except BlockingIOError:
            pass
        except OSError:
            self.close_reader()
            self.core.changed(False)

    def read_raw(self):
        try:
            # Drain pending reports; send only fresh packets, at most ten times per second.
            for _ in range(128):
                report = os.read(self.raw_fd, 64)
                if not report:
                    raise OSError("HID disconnected")
                sample = decode_report(report, self.calibration)
                if sample is None:
                    continue
                now = time.monotonic()
                self.last_packet = now
                self.core.button(bool(report[2] & 8), now)
                if self.raw_fd is None:
                    return
                if self.core.sample() and now - self.last_sent >= 0.1:
                    self.last_sent = now
                    self.sequence += 1
                    self.publish(
                        {
                            "type": "sample",
                            "epoch": self.core.epoch,
                            "sequence": self.sequence,
                            "captured_at": now,
                            **sample,
                        }
                    )
        except BlockingIOError:
            pass
        except OSError:
            self.close_reader()
            self.core.changed(False)

    def disconnect(self):
        if self.path is None:
            return
        device = dbus.Interface(
            self.bus.get_object("org.bluez", self.path, introspect=False), "org.bluez.Device1"
        )
        device.Disconnect(
            reply_handler=lambda: None,
            error_handler=lambda error: self.core.failed(
                "Disconnessione non riuscita: " + str(error)
            ),
            timeout=5,
        )
        # Stay DISCONNECTING until Connected=false is observed. Never reopen here.

    async def run(self):
        socket_path = Path(self.socket_path)
        if socket_path.exists():
            socket_path.unlink()
        server = await asyncio.start_unix_server(self.client, path=self.socket_path)
        os.chmod(self.socket_path, 0o660)
        context = GLib.MainContext.default()
        last_observation = 0
        try:
            while not self.stopping.is_set():
                for _ in range(100):
                    if not context.pending():
                        break
                    context.iteration(False)
                now = time.monotonic()
                if now - last_observation >= 1:
                    last_observation = now
                    try:
                        self.observe_bluez()
                        if self.core.device_connected and self.core.state != "DISCONNECTING":
                            if self.input is None:
                                self.open_reader()
                            elif now - self.last_packet > 2:
                                self.close_reader()
                                self.core.state = "CONNECTING"
                                self.core.failed(
                                    "Nessun nuovo campione. Riaccendi la Balance Board."
                                )
                    except (dbus.DBusException, OSError, ValueError) as error:
                        log.warning("Hardware unavailable: %s", error)
                        self.close_reader()
                        if self.core.state != "DISCONNECTING":
                            self.core.changed(False)
                        self.core.failed("Lettore Balance Board non disponibile sul Raspberry.")
                    # Status heartbeat is not a sensor sample.
                    payload = (json.dumps(self.envelope(self.core.snapshot())) + "\n").encode()
                    for writer in tuple(self.clients):
                        if not writer.is_closing():
                            writer.write(payload)
                try:
                    await asyncio.wait_for(self.stopping.wait(), 0.02)
                except TimeoutError:
                    pass
        finally:
            server.close()
            await server.wait_closed()
            self.close_reader()
            for writer in tuple(self.clients):
                writer.close()
            socket_path.unlink(missing_ok=True)


async def main():
    mac = os.environ["GRAVIA_BOARD_MAC"].upper()
    if not re.fullmatch(r"(?:[0-9A-F]{2}:){5}[0-9A-F]{2}", mac):
        raise ValueError("Invalid GRAVIA_BOARD_MAC")
    agent = Agent(mac, os.environ.get("GRAVIA_BOARD_SOCKET", "/run/gravia/balance-board.sock"))
    for signum in (signal.SIGTERM, signal.SIGINT):
        agent.loop.add_signal_handler(signum, agent.stopping.set)
    await agent.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    DBusGMainLoop(set_as_default=True)
    asyncio.run(main())
