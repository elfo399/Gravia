import asyncio
import contextlib
import json
import math
import time
from collections.abc import AsyncIterator
from dataclasses import replace

from app.balance_board.board import BoardSample, BoardStatusPublisher, BoardUnavailableError
from app.models.api_model import utc_now
from app.models.board_status import BoardStatus

STATES = {"WAITING_FOR_POWER", "CONNECTING", "CONNECTED", "DISCONNECTING"}


class BluezRealBoard:
    """Passive host-agent consumer. Socket retries never initiate Bluetooth connections."""

    def __init__(self, mac_address: str, socket_path: str, sample_timeout: float = 2):
        self.mac_address = mac_address
        self.socket_path = socket_path
        self.sample_timeout = sample_timeout
        self.status = BoardStatus(
            mode="real", connected=False, mac_address=mac_address, state="WAITING_FOR_POWER"
        )
        self._task = None
        self._publisher = None
        self._queue: asyncio.Queue[BoardSample | BoardUnavailableError] = asyncio.Queue(maxsize=1)
        self._generation = 0
        self._epoch = None
        self._sequence = -1
        self._last_packet = 0.0

    def get_status(self):
        return self.status.model_copy()

    async def start(self, publish_status: BoardStatusPublisher):
        self._publisher = publish_status
        await publish_status(self.get_status())
        self._task = asyncio.create_task(self._read_agent(), name="bluez-board-reader")

    def _deliver(self, value):
        if self._queue.full():
            self._queue.get_nowait()
        self._queue.put_nowait(value)

    async def _status(self, state, error=None):
        connected = state == "CONNECTED"
        changed = (
            self.status.state != state
            or self.status.connected != connected
            or self.status.last_error != error
        )
        if self.status.connected != connected:
            self._generation += 1
        self.status.state, self.status.connected, self.status.last_error = state, connected, error
        if not connected:
            self._deliver(BoardUnavailableError(error or "Balance Board disconnessa."))
        if changed and self._publisher is not None:
            await self._publisher(self.get_status())

    async def _consume(self, message):
        if message.get("version") != 1 or message.get("mac") != self.mac_address:
            raise ValueError("Host agent protocol or board identity mismatch")
        epoch = message["epoch"]
        if not isinstance(epoch, int) or epoch < 0:
            raise ValueError("Invalid connection epoch")
        if epoch != self._epoch:
            self._generation += 1
            self._epoch, self._sequence = epoch, -1
        if message["type"] == "status":
            state = message["state"]
            if state not in STATES:
                raise ValueError("Invalid board state")
            # CONNECTED requires fresh samples, not just an agent status heartbeat.
            if state == "CONNECTED" and time.monotonic() - self._last_packet > self.sample_timeout:
                state = "CONNECTING"
            error = message.get("error")
            if message.get("reason") == "USER_POWER_OFF" and state == "DISCONNECTING":
                error = "Misurazione interrotta dallo spegnimento della Balance Board."
            await self._status(state, error)
        elif message["type"] == "sample":
            sequence = message["sequence"]
            captured_at = message["captured_at"]
            now = time.monotonic()
            if (
                not isinstance(sequence, int)
                or sequence <= self._sequence
                or not isinstance(captured_at, (float, int))
                or not math.isfinite(captured_at)
                or not -0.5 <= now - captured_at <= self.sample_timeout
            ):
                raise ValueError("Stale or invalid sensor packet")
            values = [
                message[key] for key in ("front_left", "front_right", "rear_left", "rear_right")
            ]
            if not all(
                isinstance(value, (float, int)) and math.isfinite(value) and value >= 0
                for value in values
            ):
                raise ValueError("Invalid calibrated sensor values")
            self._last_packet, self._sequence = now, sequence
            self.status.last_sample_at = utc_now()
            await self._status("CONNECTED")
            self._deliver(BoardSample(captured_at, *values))
        else:
            raise ValueError("Unknown host agent message")

    async def _read_agent(self):
        while True:
            writer = None
            try:
                reader, writer = await asyncio.open_unix_connection(self.socket_path, limit=4096)
                self._epoch, self._sequence, self._last_packet = None, -1, 0
                while True:
                    line = await asyncio.wait_for(reader.readline(), timeout=3)
                    if not line:
                        raise OSError("Host agent disconnected")
                    await self._consume(json.loads(line))
            except (OSError, TimeoutError, ValueError, KeyError, TypeError):
                await self._status(
                    "WAITING_FOR_POWER", "Lettore Balance Board non disponibile sul Raspberry."
                )
            finally:
                if writer is not None:
                    writer.close()
                    with contextlib.suppress(OSError):
                        await writer.wait_closed()
            await asyncio.sleep(1)

    async def samples(self) -> AsyncIterator[BoardSample]:
        if not self.status.connected:
            raise BoardUnavailableError(self.status.last_error or "Balance Board non connessa.")
        generation, started = self._generation, time.monotonic()
        while not self._queue.empty():
            self._queue.get_nowait()
        while True:
            try:
                sample = await asyncio.wait_for(self._queue.get(), timeout=self.sample_timeout)
            except TimeoutError as error:
                raise BoardUnavailableError("Nessun nuovo campione dalla Balance Board.") from error
            if generation != self._generation or not self.status.connected:
                raise BoardUnavailableError(
                    self.status.last_error or "Connessione alla Balance Board interrotta."
                )
            if isinstance(sample, BoardUnavailableError):
                raise sample
            if sample.elapsed_seconds >= started:
                yield replace(sample, elapsed_seconds=sample.elapsed_seconds - started)

    async def shutdown(self):
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        await self._status("WAITING_FOR_POWER")
