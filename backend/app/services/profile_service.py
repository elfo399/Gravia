from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.activity_session import ACTIVE_ACTIVITY_STATUSES, ActivitySession
from app.models.api_model import utc_now
from app.models.measurement import Measurement
from app.models.measurement_session import ACTIVE_STATUSES, MeasurementSession
from app.models.profile import Profile, ProfileCreate, ProfileUpdate


class ProfileService:
    def __init__(self, engine):
        self.engine = engine

    def list_profiles(self):
        with Session(self.engine) as db:
            return db.exec(select(Profile).order_by(Profile.created_at)).all()

    def get_profile(self, profile_id: str):
        with Session(self.engine) as db:
            profile = db.get(Profile, profile_id)
            if profile is None:
                raise HTTPException(404, "Profilo non trovato.")
            return profile

    def create_profile(self, values: ProfileCreate):
        with Session(self.engine) as db:
            profile = Profile(**values.model_dump())
            profile.name = profile.name.strip()
            db.add(profile)
            db.commit()
            db.refresh(profile)
            return profile

    def update_profile(self, profile_id: str, values: ProfileUpdate):
        profile = self.get_profile(profile_id)
        for key, value in values.model_dump(exclude_unset=True).items():
            if key == "name" and value is None:
                raise HTTPException(422, "Il nome non può essere vuoto.")
            setattr(profile, key, value.strip() if isinstance(value, str) else value)
        profile.updated_at = utc_now()
        with Session(self.engine) as db:
            db.add(profile)
            db.commit()
            db.refresh(profile)
            return profile

    def delete_profile(self, profile_id: str):
        profile = self.get_profile(profile_id)
        with Session(self.engine) as db:
            activities = db.exec(
                select(ActivitySession).where(ActivitySession.profile_id == profile_id)
            ).all()
            if any(activity.status in ACTIVE_ACTIVITY_STATUSES for activity in activities):
                raise HTTPException(409, "Annulla il Training prima di eliminare questo profilo.")
            sessions = db.exec(
                select(MeasurementSession).where(MeasurementSession.profile_id == profile_id)
            ).all()
            if any(session.status in ACTIVE_STATUSES for session in sessions):
                raise HTTPException(409, "Annulla la sessione prima di eliminare questo profilo.")
            for measurement in db.exec(
                select(Measurement).where(Measurement.profile_id == profile_id)
            ).all():
                db.delete(measurement)
            db.flush()
            for session in sessions:
                db.delete(session)
            db.flush()
            for activity in activities:
                db.delete(activity)
            db.flush()
            db.delete(profile)
            db.commit()
