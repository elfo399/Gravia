import asyncio
import logging
import math
from contextlib import aclosing
from dataclasses import dataclass

from fastapi import HTTPException
from sqlmodel import Session, select

from app.activities.balance_hold import BalanceHold
from app.activities.symmetry import Symmetry
from app.activities.weight_shift import TARGET_COUNT, TARGET_TIMEOUT, WeightShift
from app.balance_board.board import BoardUnavailableError
from app.models.activity_session import (
    ACTIVE_ACTIVITY_STATUSES,
    ActivityCreate,
    ActivityRead,
    ActivitySession,
    ActivityStatus,
    ActivityType,
)
from app.models.api_model import utc_now
from app.services.profile_service import ProfileService

logger = logging.getLogger(__name__)
DISCONNECTED = "Balance Board disconnessa. L'attività è stata interrotta."
BOARD_BUSY = "La Balance Board è già utilizzata da un'altra attività."


@dataclass(frozen=True)
class TrainingPolicy:
    presence_seconds: float = 1.0
    countdown_seconds: float = 3.0
    step_off_seconds: float = 0.8
    live_interval: float = 0.1


class ActivityService:
    def __init__(self, engine, board, settings, live, sessions, calibration, policy=None):
        self.engine, self.board, self.settings, self.live = engine, board, settings, live
        self.sessions, self.calibration = sessions, calibration
        self.lock = sessions.lock
        self.policy = policy or TrainingPolicy()
        self.task = None
        self.elapsed = 0.0
        sessions.activities = self

    def get(self, identifier):
        with Session(self.engine) as db:
            row = db.get(ActivitySession, identifier)
            if row is None:
                raise HTTPException(404, "Attività non trovata.")
            return row

    def list(self, profile_id=None, activity_type=None):
        query = select(ActivitySession).order_by(ActivitySession.created_at.desc())
        if profile_id:
            query = query.where(ActivitySession.profile_id == profile_id)
        if activity_type:
            query = query.where(ActivitySession.activity_type == activity_type)
        with Session(self.engine) as db:
            return db.exec(query).all()

    def get_active_session(self):
        with Session(self.engine) as db:
            return db.exec(
                select(ActivitySession).where(ActivitySession.status.in_(ACTIVE_ACTIVITY_STATUSES))
            ).first()

    @property
    def is_active(self):
        return self.get_active_session() is not None or (
            self.task is not None and not self.task.done()
        )

    def recover_interrupted_sessions(self):
        with Session(self.engine) as db:
            for row in db.exec(
                select(ActivitySession).where(ActivitySession.status.in_(ACTIVE_ACTIVITY_STATUSES))
            ).all():
                row.status = ActivityStatus.ERROR
                row.completed_at = utc_now()
                row.error_message = "Attività interrotta dal riavvio dell'applicazione."
                db.add(row)
            db.commit()

    async def start(self, values: ActivityCreate):
        if self.lock.locked():
            raise HTTPException(409, BOARD_BUSY)
        async with self.lock:
            ProfileService(self.engine).get_profile(values.profile_id)
            if (
                self.is_active
                or self.sessions.get_active_session()
                or (self.sessions.task and not self.sessions.task.done())
                or self.calibration.is_active
            ):
                raise HTTPException(409, BOARD_BUSY)
            if not self.board.get_status().connected:
                raise HTTPException(503, "Accendi la Balance Board per iniziare.")
            duration = (
                TARGET_COUNT * TARGET_TIMEOUT
                if values.activity_type == ActivityType.WEIGHT_SHIFT
                else values.duration_seconds
            )
            with Session(self.engine) as db:
                row = ActivitySession(
                    profile_id=values.profile_id,
                    activity_type=values.activity_type,
                    duration_seconds=duration,
                )
                db.add(row)
                db.commit()
                db.refresh(row)
            self.elapsed = 0.0
            await self.publish_status(row)
            self.task = asyncio.create_task(self.run(row.id), name=f"training-{row.id}")
            return row

    async def publish_status(self, row, countdown=None):
        await self.live.publish(
            {
                "type": "activity_status",
                "activitySessionId": row.id,
                "profileId": row.profile_id,
                "activityType": row.activity_type,
                "status": row.status,
                "countdown": countdown,
                "durationSeconds": row.duration_seconds,
                "message": row.error_message,
            }
        )

    async def change_status(self, identifier, status, countdown=None):
        with Session(self.engine) as db:
            row = db.get(ActivitySession, identifier)
            if row.status not in ACTIVE_ACTIVITY_STATUSES:
                return row
            if row.status != status:
                row.status = status
                db.add(row)
                db.commit()
                db.refresh(row)
        await self.publish_status(row, countdown)
        return row

    async def finish(self, identifier, status, exercise=None, message=None):
        with Session(self.engine) as db:
            row = db.get(ActivitySession, identifier)
            if row.status not in ACTIVE_ACTIVITY_STATUSES:
                return row
            row.status, row.completed_at, row.error_message = status, utc_now(), message
            row.duration_seconds = self.elapsed
            if status == ActivityStatus.COMPLETED:
                row.score, row.result_json = exercise.score, exercise.get_result()
            db.add(row)
            db.commit()
            db.refresh(row)
        await self.publish_status(row)
        if status == ActivityStatus.COMPLETED:
            await self.live.publish(
                {
                    "type": "activity_completed",
                    "activitySessionId": row.id,
                    "activity": ActivityRead.model_validate(row).model_dump(
                        mode="json", by_alias=True
                    ),
                }
            )
        return row

    async def cancel(self, identifier):
        async with self.lock:
            row = self.get(identifier)
            if row.status not in ACTIVE_ACTIVITY_STATUSES:
                raise HTTPException(409, "L'attività è già terminata.")
            if self.task and not self.task.done():
                self.task.cancel()
                await asyncio.gather(self.task, return_exceptions=True)
            return await self.finish(identifier, ActivityStatus.CANCELLED)

    async def on_board_status(self, status):
        if status.connected or not self.get_active_session():
            return
        async with self.lock:
            row = self.get_active_session()
            if row:
                if self.task and not self.task.done():
                    self.task.cancel()
                    await asyncio.gather(self.task, return_exceptions=True)
                await self.finish(row.id, ActivityStatus.ERROR, message=DISCONNECTED)

    async def run(self, identifier):
        row = self.get(identifier)
        if row.activity_type == ActivityType.BALANCE_HOLD:
            exercise = BalanceHold()
        elif row.activity_type == ActivityType.SYMMETRY:
            exercise = Symmetry()
        else:
            exercise = WeightShift(identifier)
        presence_since = countdown_since = active_since = below_since = previous_time = None
        previous_present = False
        countdown_value = None
        previous_live = -1.0
        try:
            timeout = (
                self.settings.session_timeout + row.duration_seconds + self.policy.countdown_seconds
            )
            async with asyncio.timeout(timeout), aclosing(self.board.samples()) as stream:
                while True:
                    try:
                        sample = await asyncio.wait_for(
                            anext(stream), self.settings.board_sample_timeout
                        )
                    except (TimeoutError, StopAsyncIteration) as error:
                        raise BoardUnavailableError(DISCONNECTED) from error
                    now = sample.elapsed_seconds
                    values = (
                        now,
                        sample.front_left,
                        sample.front_right,
                        sample.rear_left,
                        sample.rear_right,
                    )
                    if not all(math.isfinite(value) for value in values) or now < 0:
                        raise RuntimeError("La board ha restituito una lettura non valida.")
                    if previous_time is not None and (
                        now <= previous_time
                        or now - previous_time > self.settings.board_sample_timeout
                    ):
                        raise RuntimeError("Flusso di campioni interrotto. Attività interrotta.")
                    if not self.board.get_status().connected:
                        raise BoardUnavailableError(DISCONNECTED)
                    present = sample.weight >= self.settings.minimum_weight
                    if active_since is None:
                        if not present:
                            presence_since = countdown_since = None
                            countdown_value = None
                            if row.status != ActivityStatus.WAITING_FOR_USER:
                                row = await self.change_status(
                                    identifier, ActivityStatus.WAITING_FOR_USER
                                )
                        else:
                            if presence_since is None:
                                presence_since = now
                            if (
                                countdown_since is None
                                and now - presence_since >= self.policy.presence_seconds - 1e-9
                            ):
                                countdown_since = now
                            if countdown_since is not None:
                                remaining = self.policy.countdown_seconds - (now - countdown_since)
                                if remaining <= 1e-9:
                                    active_since = now
                                    row = await self.change_status(
                                        identifier, ActivityStatus.ACTIVE, 0
                                    )
                                else:
                                    value = math.ceil(remaining - 1e-9)
                                    if value != countdown_value:
                                        row = await self.change_status(
                                            identifier, ActivityStatus.COUNTDOWN, value
                                        )
                                        countdown_value = value
                    if active_since is not None:
                        self.elapsed = now - active_since
                        if not present:
                            if below_since is None:
                                below_since = now
                            if isinstance(exercise, WeightShift):
                                exercise.interrupt_hold()
                            if now - below_since >= self.policy.step_off_seconds - 1e-9:
                                raise RuntimeError(
                                    "Sei sceso dalla Balance Board. Attività interrotta."
                                )
                        else:
                            below_since = None
                            elapsed = (
                                self.elapsed
                                if isinstance(exercise, WeightShift)
                                else min(self.elapsed, row.duration_seconds)
                            )
                            previous_elapsed = (
                                max(0, previous_time - active_since)
                                if previous_time is not None
                                else 0
                            )
                            dt = max(0, elapsed - previous_elapsed) if previous_present else 0
                            data = exercise.process_sample(sample, elapsed, dt)
                            if now - previous_live >= self.policy.live_interval - 1e-9:
                                previous_live = now
                                await self.live.publish(
                                    {
                                        "type": "activity_live",
                                        "activitySessionId": identifier,
                                        "elapsed": elapsed,
                                        "remaining": max(0, row.duration_seconds - elapsed),
                                        "score": exercise.score,
                                        "weight": round(sample.weight, 3),
                                        "centerOfPressure": {
                                            "x": sample.center_x,
                                            "y": sample.center_y,
                                        },
                                        "data": data,
                                    }
                                )
                            complete = (
                                exercise.completed
                                if isinstance(exercise, WeightShift)
                                else self.elapsed >= row.duration_seconds
                            )
                            if complete:
                                self.elapsed = elapsed
                                await self.finish(identifier, ActivityStatus.COMPLETED, exercise)
                                return
                    previous_time, previous_present = now, present
        except asyncio.CancelledError:
            raise
        except BoardUnavailableError:
            await self.finish(identifier, ActivityStatus.ERROR, message=DISCONNECTED)
        except TimeoutError:
            await self.finish(
                identifier, ActivityStatus.ERROR, message="Tempo scaduto. Riprova l'attività."
            )
        except Exception as error:
            logger.exception("Training session failed")
            message = (
                str(error) if isinstance(error, RuntimeError) else "Attività interrotta. Riprova."
            )
            await self.finish(identifier, ActivityStatus.ERROR, message=message)

    async def shutdown(self):
        row = self.get_active_session()
        if row:
            if self.task and not self.task.done():
                self.task.cancel()
                await asyncio.gather(self.task, return_exceptions=True)
            await self.finish(
                row.id,
                ActivityStatus.ERROR,
                message="Attività interrotta dal riavvio dell'applicazione.",
            )
