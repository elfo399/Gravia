from datetime import UTC, datetime

from fastapi import HTTPException
from sqlmodel import Session, select

from app.balance_board.board import BoardSample
from app.models.measurement import Measurement, MeasurementUpdate
from app.models.measurement_session import MeasurementSession, SessionStatus


class MeasurementService:
    def __init__(self, engine):
        self.engine = engine

    def list_measurements(self, profile_id=None, from_date=None, to_date=None):
        from_date = self.normalize_filter_date(from_date)
        to_date = self.normalize_filter_date(to_date)
        if from_date and to_date and from_date > to_date:
            raise HTTPException(422, "Il periodo selezionato non è valido.")
        query = select(Measurement).order_by(Measurement.measured_at.desc())
        if profile_id:
            query = query.where(Measurement.profile_id == profile_id)
        if from_date:
            query = query.where(Measurement.measured_at >= from_date)
        if to_date:
            query = query.where(Measurement.measured_at <= to_date)
        with Session(self.engine) as db:
            return db.exec(query).all()

    @staticmethod
    def normalize_filter_date(value):
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

    def get_measurement(self, measurement_id: str):
        with Session(self.engine) as db:
            result = db.get(Measurement, measurement_id)
            if result is None:
                raise HTTPException(404, "Misurazione non trovata.")
            return result

    def update_measurement(self, measurement_id: str, values: MeasurementUpdate):
        result = self.get_measurement(measurement_id)
        for key, value in values.model_dump(exclude_unset=True).items():
            setattr(result, key, value)
        with Session(self.engine) as db:
            db.add(result)
            db.commit()
            db.refresh(result)
            return result

    def delete_measurement(self, measurement_id: str):
        result = self.get_measurement(measurement_id)
        with Session(self.engine) as db:
            db.delete(result)
            db.commit()

    def save_completed_measurement(
        self, session_id: str, sample: BoardSample, stability: float, average_weight: float
    ):
        with Session(self.engine) as db:
            session = db.get(MeasurementSession, session_id)
            if session is None or session.status != SessionStatus.STABILIZING:
                raise ValueError("Only a stabilizing session can complete.")
            # Scale the four sensors together to preserve balance and sum to final weight.
            final_weight = round(average_weight, 3)
            scale = final_weight / sample.weight
            measurement = Measurement(
                session_id=session.id,
                profile_id=session.profile_id,
                weight=final_weight,
                stability=stability,
                front_left=sample.front_left * scale,
                front_right=sample.front_right * scale,
                rear_left=sample.rear_left * scale,
                rear_right=sample.rear_right * scale,
                center_x=sample.center_x,
                center_y=sample.center_y,
            )
            session.status = SessionStatus.COMPLETED
            session.ended_at = datetime.now(UTC)
            db.add(measurement)
            db.add(session)
            db.commit()
            db.refresh(measurement)
            return measurement
