import asyncio
import logging

from fastapi import HTTPException
from sqlmodel import Session, select

from app.balance_board.board import BalanceBoard, BoardUnavailableError
from app.configuration import Settings
from app.models.api_model import utc_now
from app.models.measurement import MeasurementRead
from app.models.measurement_session import ACTIVE_STATUSES, MeasurementSession, SessionStatus
from app.services.measurement_service import MeasurementService
from app.services.profile_service import ProfileService
from app.services.stability_service import StabilityService
from app.websocket.live_measurements import LiveMeasurements

logger = logging.getLogger(__name__)


class SessionService:
    def __init__(self, engine, board: BalanceBoard, settings: Settings, live: LiveMeasurements):
        self.engine = engine
        self.board = board
        self.settings = settings
        self.live = live
        self.task: asyncio.Task | None = None
        self.lock = asyncio.Lock()
        self.calibration = None
        self.measurements = MeasurementService(engine)

    def get_session(self, session_id: str):
        with Session(self.engine) as db:
            session = db.get(MeasurementSession, session_id)
            if session is None:
                raise HTTPException(404, "Sessione non trovata.")
            return session

    def get_active_session(self):
        with Session(self.engine) as db:
            return db.exec(
                select(MeasurementSession).where(MeasurementSession.status.in_(ACTIVE_STATUSES))
            ).first()

    def recover_interrupted_sessions(self):
        with Session(self.engine) as db:
            for session in db.exec(
                select(MeasurementSession).where(MeasurementSession.status.in_(ACTIVE_STATUSES))
            ).all():
                session.status = SessionStatus.ERROR
                session.ended_at = utc_now()
                session.error_message = "Sessione interrotta dal riavvio dell'applicazione."
                db.add(session)
            db.commit()

    async def start_measurement_session(self, profile_id: str):
        if self.calibration and self.calibration.is_active:
            raise HTTPException(
                409, "Completa o annulla la calibrazione prima di iniziare una pesata."
            )
        async with self.lock:
            if self.calibration and self.calibration.is_active:
                raise HTTPException(
                    409, "Completa o annulla la calibrazione prima di iniziare una pesata."
                )
            ProfileService(self.engine).get_profile(profile_id)
            if self.get_active_session() or (self.task and not self.task.done()):
                raise HTTPException(409, "Una sessione è già attiva. Attendi o annullala.")
            board_status = self.board.get_status()
            if not board_status.connected:
                raise HTTPException(
                    503,
                    board_status.last_error or "Balance Board non connessa. Accendila e riprova.",
                )
            with Session(self.engine) as db:
                session = MeasurementSession(profile_id=profile_id)
                db.add(session)
                db.commit()
                db.refresh(session)
            await self.publish_status(session)
            self.task = asyncio.create_task(self.run_measurement_session(session.id))
            return session

    async def publish_status(self, session, stability=0):
        await self.live.publish(
            {
                "type": "session_status",
                "sessionId": session.id,
                "profileId": session.profile_id,
                "status": session.status,
                "stability": stability,
                "message": session.error_message,
            }
        )

    async def change_status(self, session_id, status, stability=0, message=None):
        with Session(self.engine) as db:
            session = db.get(MeasurementSession, session_id)
            session.status = status
            session.error_message = message
            if status not in ACTIVE_STATUSES:
                session.ended_at = utc_now()
            db.add(session)
            db.commit()
            db.refresh(session)
        await self.publish_status(session, stability)
        return session

    async def cancel_measurement_session(self, session_id: str):
        async with self.lock:
            session = self.get_session(session_id)
            if session.status not in ACTIVE_STATUSES:
                raise HTTPException(409, "La sessione è già terminata.")
            if self.task and not self.task.done():
                self.task.cancel()
                try:
                    await self.task
                except asyncio.CancelledError:
                    pass
            return await self.change_status(session_id, SessionStatus.CANCELLED)

    async def run_measurement_session(self, session_id: str):
        stability = StabilityService(
            self.settings.minimum_weight,
            self.settings.required_stability,
            self.settings.stable_duration,
            self.settings.stability_range_kg,
            self.settings.stability_stddev_kg,
        )
        try:
            async with asyncio.timeout(self.settings.session_timeout):
                async for sample in self.board.samples():
                    result = stability.calculate_weight_stability(
                        sample.elapsed_seconds, sample.weight
                    )
                    session = self.get_session(session_id)
                    if sample.weight < self.settings.minimum_weight:
                        status = SessionStatus.WAITING_FOR_USER
                    elif result.score >= self.settings.required_stability:
                        status = SessionStatus.STABILIZING
                    else:
                        status = SessionStatus.MEASURING
                    if status != session.status:
                        await self.change_status(session_id, status, result.score)
                    await self.live.publish(
                        {
                            "type": "live_measurement",
                            "sessionId": session_id,
                            "weight": round(sample.weight, 3),
                            "stability": result.score,
                            "sensors": {
                                "frontLeft": sample.front_left,
                                "frontRight": sample.front_right,
                                "rearLeft": sample.rear_left,
                                "rearRight": sample.rear_right,
                            },
                            "centerOfPressure": {"x": sample.center_x, "y": sample.center_y},
                        }
                    )
                    if result.stable:
                        measurement = self.measurements.save_completed_measurement(
                            session_id, sample, result.score, result.average_weight
                        )
                        await self.publish_status(self.get_session(session_id), result.score)
                        await self.live.publish(
                            {
                                "type": "measurement_completed",
                                "sessionId": session_id,
                                "measurement": MeasurementRead.model_validate(
                                    measurement
                                ).model_dump(mode="json", by_alias=True),
                            }
                        )
                        return
                raise RuntimeError("La Balance Board ha interrotto il flusso di dati.")
        except TimeoutError:
            await self.fail_session(session_id, "Tempo scaduto. Riprova la misurazione.")
        except asyncio.CancelledError:
            raise
        except BoardUnavailableError as error:
            logger.warning("Measurement interrupted: %s", error)
            await self.fail_session(session_id, str(error))
        except Exception as error:
            logger.exception("Measurement session failed")
            message = (
                str(error)
                if isinstance(error, RuntimeError)
                else "Errore durante la misurazione. Riprova."
            )
            await self.fail_session(session_id, message)

    async def fail_session(self, session_id, message):
        await self.change_status(session_id, SessionStatus.ERROR, message=message)
        await self.live.publish({"type": "error", "sessionId": session_id, "message": message})

    async def shutdown(self):
        active = self.get_active_session()
        if active:
            await self.cancel_measurement_session(active.id)
