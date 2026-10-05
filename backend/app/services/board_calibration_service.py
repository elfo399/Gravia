import asyncio
import math
import statistics
import time
from contextlib import aclosing
from dataclasses import dataclass, field, replace

from fastapi import HTTPException
from sqlmodel import Session, select

from app.balance_board.board import BoardUnavailableError
from app.models.api_model import new_id, utc_now
from app.models.board_calibration import (
    BoardCalibration,
    BoardCalibrationRead,
    BoardCalibrationStatus,
    CalibrationSessionRead,
)

SENSORS = ("front_left", "front_right", "rear_left", "rear_right")
DISCONNECTED = "Calibrazione interrotta perché la Balance Board si è disconnessa."


@dataclass(frozen=True)
class CalibrationPolicy:
    window_seconds: float = 4
    minimum_samples: int = 30
    sample_timeout: float = 2
    maximum_tare_kg: float = 2
    maximum_range_kg: float = 0.5
    maximum_stddev_kg: float = 0.15
    minimum_scale: float = 0.75
    maximum_scale: float = 1.25
    tolerance_kg: float = 0.2
    tolerance_fraction: float = 0.01
    session_seconds: float = 600


@dataclass
class CalibrationSession:
    board_mac: str
    expires_at: float
    result: CalibrationSessionRead = field(
        default_factory=lambda: CalibrationSessionRead(id=new_id(), stage="TARE")
    )
    offsets: tuple[float, ...] | None = None


class BoardCalibrationService:
    def __init__(self, engine, hardware, sessions, policy=None):
        self.engine, self.hardware, self.sessions = engine, hardware, sessions
        self.lock = sessions.lock
        self.policy = policy or CalibrationPolicy()
        self.active: CalibrationSession | None = None
        self.acquisition = None
        self.aborted = None
        self.cache_mac = None
        self.cached: BoardCalibration | None = None
        self.publish_status = None
        self.watchdog = None

    @property
    def is_active(self):
        return self.active is not None and time.monotonic() < self.active.expires_at

    async def watch(self):
        while True:
            await asyncio.sleep(1)
            if self.active and not self.is_active:
                self.abort("Calibrazione scaduta. Inizia una nuova calibrazione.")
            self.on_board_status(self.hardware.get_status())

    def current(self):
        status = self.hardware.get_status()
        mac = status.mac_address if status.mode == "real" else None
        if mac != self.cache_mac:
            with Session(self.engine) as db:
                self.cached = (
                    db.exec(
                        select(BoardCalibration).where(BoardCalibration.board_mac == mac)
                    ).first()
                    if mac
                    else None
                )
            self.cache_mac = mac
        return self.cached

    def read(self):
        calibration = self.current()
        return BoardCalibrationStatus(
            configured=calibration is not None,
            calibration=BoardCalibrationRead.model_validate(calibration) if calibration else None,
            active_session=self.active.result.model_copy() if self.is_active else None,
        )

    def apply(self, sample):
        calibration = self.current()
        if calibration is None:
            return sample
        values = {
            sensor: max(0, getattr(sample, sensor) - getattr(calibration, sensor + "_offset"))
            * calibration.weight_scale
            for sensor in SENSORS
        }
        return replace(sample, **values)

    async def notify(self):
        if self.publish_status:
            await self.publish_status(self.hardware.get_status())

    def abort(self, message):
        if self.active is not None:
            self.aborted = (self.active.result.id, message)
            self.active = None
            if self.acquisition and not self.acquisition.done():
                self.acquisition.cancel()
            if self.publish_status:
                asyncio.create_task(self.notify())

    def on_board_status(self, status):
        if self.active and (not status.connected or status.mac_address != self.active.board_mac):
            self.abort(DISCONNECTED)

    def _available(self):
        status = self.hardware.get_status()
        if status.mode != "real":
            raise HTTPException(409, "La calibrazione è disponibile soltanto con la board reale.")
        if not status.connected or not status.mac_address:
            raise HTTPException(503, "Accendi la Balance Board prima di iniziare la calibrazione.")
        return status

    def _session(self, identifier):
        if self.active and not self.is_active:
            self.abort("Calibrazione scaduta. Inizia una nuova calibrazione.")
        if not self.is_active or self.active.result.id != identifier:
            if self.aborted and self.aborted[0] == identifier:
                raise HTTPException(409, self.aborted[1])
            raise HTTPException(404, "Sessione di calibrazione non trovata.")
        self.on_board_status(self.hardware.get_status())
        if self.active is None:
            raise HTTPException(409, DISCONNECTED)
        return self.active

    async def start(self):
        if self.is_active or self.lock.locked():
            raise HTTPException(409, "Una calibrazione o una misurazione è già in corso.")
        async with self.lock:
            status = self._available()
            if self.sessions.get_active_session():
                raise HTTPException(409, "Termina la misurazione prima di calibrare la board.")
            self.active = CalibrationSession(
                status.mac_address, time.monotonic() + self.policy.session_seconds
            )
            identifier = self.active.result.id
            await self.notify()
            return self._session(identifier).result.model_copy()

    async def cancel(self, identifier):
        session = self._session(identifier)
        self.abort("Calibrazione annullata.")
        await self.notify()
        return session.result

    async def _collect(self, session):
        samples = []
        started = time.monotonic()
        async with asyncio.timeout(self.policy.window_seconds + self.policy.sample_timeout):
            async with aclosing(self.hardware.samples()) as stream:
                async for sample in stream:
                    self._session(session.result.id)
                    values = [getattr(sample, sensor) for sensor in SENSORS]
                    if not math.isfinite(sample.weight) or not all(
                        math.isfinite(value) and value >= 0 for value in values
                    ):
                        raise HTTPException(422, "La board ha restituito una lettura non valida.")
                    samples.append(sample)
                    if (
                        time.monotonic() - started >= self.policy.window_seconds
                        and len(samples) >= self.policy.minimum_samples
                    ):
                        break
                else:
                    raise BoardUnavailableError(DISCONNECTED)
        weights = [sample.weight for sample in samples]
        if (
            max(weights) - min(weights) > self.policy.maximum_range_kg
            or statistics.pstdev(weights) > self.policy.maximum_stddev_kg
        ):
            raise HTTPException(
                422, "Il peso non è abbastanza stabile. Attendi qualche secondo e riprova."
            )
        return tuple(
            statistics.mean(getattr(sample, sensor) for sample in samples) for sensor in SENSORS
        )

    async def acquire(self, identifier, action, reference_weight=None):
        session = self._session(identifier)
        if session.result.busy or self.lock.locked():
            raise HTTPException(409, "Acquisizione già in corso. Attendi il risultato.")
        expected = {"tare": "TARE", "reference": "REFERENCE", "verify": "VERIFY"}[action]
        if session.result.stage != expected:
            raise HTTPException(409, "Completa prima il passaggio precedente.")
        if action == "reference" and (
            not isinstance(reference_weight, (float, int))
            or not math.isfinite(reference_weight)
            or not 0 < reference_weight <= 150
        ):
            raise HTTPException(422, "Inserisci un peso noto maggiore di zero, fino a 150 kg.")
        async with self.lock:
            self._session(identifier)
            session.result.busy = True
            if action == "verify":
                # A failed retry must never leave an earlier successful check saveable.
                session.result.valid = None
                session.result.measured_weight_after = None
                session.result.absolute_error = None
                session.result.percentage_error = None
            try:
                self.acquisition = asyncio.create_task(self._collect(session))
                averages = await self.acquisition
                self._session(identifier)
                if action == "tare":
                    if sum(averages) > self.policy.maximum_tare_kg:
                        raise HTTPException(
                            422,
                            "La Balance Board sembra avere del peso sopra. "
                            "Rimuovi tutto dalla pedana e riprova.",
                        )
                    session.offsets = averages
                    session.result.stage = "REFERENCE"
                else:
                    measured = sum(
                        max(0, value - offset)
                        for value, offset in zip(averages, session.offsets, strict=True)
                    )
                    if measured <= 0:
                        raise HTTPException(
                            422, "Posiziona il peso conosciuto al centro della Balance Board."
                        )
                    if action == "reference":
                        scale = reference_weight / measured
                        if not self.policy.minimum_scale <= scale <= self.policy.maximum_scale:
                            raise HTTPException(
                                422,
                                "Il peso letto non è compatibile con quello indicato. "
                                "Controlla il peso noto e riprova.",
                            )
                        session.result.reference_weight = reference_weight
                        session.result.weight_scale = scale
                        session.result.measured_weight_before = sum(averages)
                        session.result.stage = "VERIFY"
                    else:
                        after = measured * session.result.weight_scale
                        error = after - session.result.reference_weight
                        session.result.measured_weight_after = after
                        session.result.absolute_error = error
                        session.result.percentage_error = (
                            100 * error / session.result.reference_weight
                        )
                        session.result.valid = abs(error) <= max(
                            self.policy.tolerance_kg,
                            self.policy.tolerance_fraction * session.result.reference_weight,
                        )
                return session.result.model_copy()
            except (BoardUnavailableError, asyncio.CancelledError) as error:
                message = (
                    self.aborted[1]
                    if self.aborted and self.aborted[0] == identifier
                    else DISCONNECTED
                )
                self.abort(message)
                raise HTTPException(409, message) from error
            except TimeoutError as error:
                self.abort("Acquisizione interrotta: non arrivano abbastanza campioni dalla board.")
                raise HTTPException(409, self.aborted[1]) from error
            finally:
                session.result.busy = False
                self.acquisition = None

    async def save(self, identifier):
        session = self._session(identifier)
        if session.result.busy or self.lock.locked():
            raise HTTPException(409, "Attendi la fine dell'acquisizione.")
        async with self.lock:
            self._session(identifier)
            if session.result.valid is not True:
                raise HTTPException(409, "Verifica la calibrazione prima di salvarla.")
            result = session.result
            with Session(self.engine) as db:
                row = db.exec(
                    select(BoardCalibration).where(BoardCalibration.board_mac == session.board_mac)
                ).first() or BoardCalibration(board_mac=session.board_mac)
                for sensor, offset in zip(SENSORS, session.offsets, strict=True):
                    setattr(row, sensor + "_offset", offset)
                for name in (
                    "weight_scale",
                    "reference_weight",
                    "measured_weight_before",
                    "measured_weight_after",
                ):
                    setattr(row, name, getattr(result, name))
                row.calibrated_at = utc_now()
                db.add(row)
                db.commit()
                db.refresh(row)
                self.cached, self.cache_mac = row, session.board_mac
            self.active = None
            await self.notify()
            return self.read()

    async def reset(self):
        if self.is_active or self.lock.locked():
            raise HTTPException(409, "Termina la calibrazione prima di ripristinare.")
        async with self.lock:
            if self.sessions.get_active_session():
                raise HTTPException(409, "Termina la misurazione prima di ripristinare.")
            self._available_mode()
            current = self.current()
            if current:
                with Session(self.engine) as db:
                    db.delete(db.get(BoardCalibration, current.id))
                    db.commit()
            self.cached = None
            return self.read()

    def _available_mode(self):
        if self.hardware.get_status().mode != "real":
            raise HTTPException(409, "La calibrazione è disponibile soltanto con la board reale.")

    async def shutdown(self):
        if self.watchdog:
            self.watchdog.cancel()
            await asyncio.gather(self.watchdog, return_exceptions=True)
        self.abort("Calibrazione interrotta dal riavvio dell'applicazione.")
        if self.acquisition:
            await asyncio.gather(self.acquisition, return_exceptions=True)
