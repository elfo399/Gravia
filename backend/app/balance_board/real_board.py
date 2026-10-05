import asyncio
import errno
import logging
import math
import threading
import time
from collections.abc import AsyncIterator
from dataclasses import replace

from wiibalance.state import BoardState

from app.balance_board.board import BoardSample, BoardStatusPublisher, BoardUnavailableError
from app.balance_board.wiibalance_client import WiibalanceClient
from app.models.api_model import utc_now
from app.models.board_status import BoardStatus

logger = logging.getLogger(__name__)
RECONNECT_DELAYS = (2, 5, 10)


def map_board_state(state: BoardState, elapsed_seconds: float) -> BoardSample:
    """Wii top = Gravia front, bottom = rear; fix physical orientation only here."""
    weights = state.weights
    sample = BoardSample(
        elapsed_seconds,
        front_left=weights.top_left,
        front_right=weights.top_right,
        rear_left=weights.bottom_left,
        rear_right=weights.bottom_right,
    )
    if not all(
        math.isfinite(value) and value >= 0
        for value in (sample.front_left, sample.front_right, sample.rear_left, sample.rear_right)
    ):
        raise BoardUnavailableError("La Balance Board ha restituito sensori non validi.")
    return sample


def describe_connection_error(error: Exception) -> str:
    if isinstance(error, BoardUnavailableError):
        return str(error)
    if isinstance(error, PermissionError):
        return "Accesso Bluetooth negato. Controlla i permessi del container sul Raspberry."
    if isinstance(error, OSError) and error.errno in (errno.EAFNOSUPPORT, errno.EPROTONOSUPPORT):
        return "Socket Bluetooth L2CAP non disponibile. Usa l'override Raspberry con rete host."
    if isinstance(error, OSError) and error.errno in (errno.ENODEV, errno.ENETDOWN):
        return "Adattatore Bluetooth non disponibile o spento sul Raspberry."
    if isinstance(error, TimeoutError):
        return "Nessun nuovo campione dalla Balance Board. Accendila e riprova."
    return "Board non connessa. Controlla pairing e adattatore, poi premi SYNC se necessario."


class RealBoard:
    """One persistent connection; session cancellation only detaches the consumer."""

    def __init__(self, mac_address: str, sample_timeout: float = 2):
        self.mac_address = mac_address
        self.sample_timeout = sample_timeout
        self.status = BoardStatus(mode="real", connected=False, mac_address=mac_address)
        self._connection = None
        self._connection_lock = threading.Lock()
        self._stopping = threading.Event()
        self._stop_wait = asyncio.Event()
        self._reader_task: asyncio.Task | None = None
        self._publish_status: BoardStatusPublisher | None = None
        self._samples: asyncio.Queue[BoardSample | BoardUnavailableError] = asyncio.Queue(maxsize=1)
        self._generation = 0
        self._last_weights = None
        self._last_packet_at = 0.0
        self._battery = None

    async def start(self, publish_status: BoardStatusPublisher):
        self._publish_status = publish_status
        await publish_status(self.get_status())
        self._reader_task = asyncio.create_task(self._read_continuously(), name="real-board-reader")

    def get_status(self) -> BoardStatus:
        return self.status.model_copy()

    def _connect(self):
        logger.info("Connecting to Wii Balance Board %s", self.mac_address)
        connection = WiibalanceClient(self.mac_address)
        with self._connection_lock:
            stopping = self._stopping.is_set()
            if not stopping:
                self._connection = connection
        if stopping:
            connection.close()
            return
        self._last_weights = None
        self._last_packet_at = time.monotonic()

    def _read_sample(self) -> BoardSample | None:
        with self._connection_lock:
            connection = self._connection
        if connection is None:
            raise BoardUnavailableError("Balance Board disconnessa.")
        state = connection.read_state()
        if not state.connected:
            raise BoardUnavailableError("Connessione alla Balance Board interrotta.")
        captured_at = time.monotonic()
        # read_state is a snapshot. The verified library replaces Weights for each DATA packet.
        # Reusing the same object would turn stale data into a falsely stable measurement.
        if state.weights is self._last_weights:
            if captured_at - self._last_packet_at >= self.sample_timeout:
                raise TimeoutError("Balance Board sample stream stalled")
            return None
        sample = map_board_state(state, captured_at)
        self._last_weights = state.weights
        self._last_packet_at = captured_at
        self._battery = state.battery_percent if state.battery_raw >= 0 else None
        return sample

    def _disconnect(self):
        with self._connection_lock:
            connection, self._connection = self._connection, None
        if connection is not None:
            connection.close()

    def _deliver(self, sample: BoardSample | BoardUnavailableError):
        if self._samples.full():
            self._samples.get_nowait()
        self._samples.put_nowait(sample)

    async def _set_connection_status(self, connected: bool, error: str | None = None):
        changed = self.status.connected != connected or self.status.last_error != error
        if self.status.connected != connected:
            self._generation += 1
        self.status.connected = connected
        self.status.last_error = error
        if not connected:
            self.status.battery = None
            self._deliver(BoardUnavailableError(error or "Balance Board non connessa."))
        if changed and self._publish_status is not None:
            await self._publish_status(self.get_status())

    async def _wait_or_stop(self, seconds: float):
        try:
            await asyncio.wait_for(self._stop_wait.wait(), timeout=seconds)
        except TimeoutError:
            pass

    async def _read_continuously(self):
        retry_index = 0
        while not self._stopping.is_set():
            try:
                if self._connection is None:
                    await asyncio.to_thread(self._connect)
                if self._stopping.is_set():
                    break
                sample = await asyncio.to_thread(self._read_sample)
                if self._stopping.is_set():
                    break
                if sample is not None:
                    self.status.last_sample_at = utc_now()
                    self.status.battery = self._battery
                    if not self.status.connected:
                        logger.info("Wii Balance Board connected: %s", self.mac_address)
                        await self._set_connection_status(True)
                    self._deliver(sample)
                    retry_index = 0
                await self._wait_or_stop(0.1)
            except Exception as error:
                if self._stopping.is_set():
                    break
                message = describe_connection_error(error)
                logger.warning("Wii Balance Board disconnected: %s (%s)", message, error)
                await self._set_connection_status(False, message)
                try:
                    await asyncio.to_thread(self._disconnect)
                except Exception:
                    logger.exception("Unable to close Wii Balance Board reader")
                    await self._set_connection_status(
                        False, "Errore nella chiusura del lettore Bluetooth."
                    )
                    return
                delay = RECONNECT_DELAYS[min(retry_index, len(RECONNECT_DELAYS) - 1)]
                retry_index += 1
                logger.info("Retrying Wii Balance Board connection in %s seconds", delay)
                await self._wait_or_stop(delay)

    async def samples(self) -> AsyncIterator[BoardSample]:
        if not self.status.connected:
            raise BoardUnavailableError(self.status.last_error or "Balance Board non connessa.")
        generation = self._generation
        started = time.monotonic()
        while not self._samples.empty():
            self._samples.get_nowait()
        while True:
            sample = await self._samples.get()
            if generation != self._generation or not self.status.connected:
                raise BoardUnavailableError("Connessione alla Balance Board interrotta. Riprova.")
            if isinstance(sample, BoardUnavailableError):
                raise sample
            if sample.elapsed_seconds >= started:
                yield replace(sample, elapsed_seconds=sample.elapsed_seconds - started)

    async def shutdown(self):
        self._stopping.set()
        self._stop_wait.set()
        try:
            # Closing an existing socket wakes blocking reads. An in-flight constructor is
            # awaited (never cancelled/abandoned) and closes its result when stopping is set.
            await asyncio.to_thread(self._disconnect)
        finally:
            if self._reader_task is not None:
                await self._reader_task
            self.status.connected = False
