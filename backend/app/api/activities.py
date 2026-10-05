from typing import Annotated

from fastapi import APIRouter, Query, Request

from app.models.activity_session import ActivityCreate, ActivityRead, ActivityType

router = APIRouter(prefix="/api/v1/activities", tags=["Training"])


@router.post("", response_model=ActivityRead, status_code=201)
async def start(request: Request, values: ActivityCreate):
    return await request.app.state.activities.start(values)


@router.get("", response_model=list[ActivityRead])
def list_activities(
    request: Request,
    profile_id: Annotated[str | None, Query(alias="profileId")] = None,
    activity_type: Annotated[ActivityType | None, Query(alias="activityType")] = None,
):
    return request.app.state.activities.list(profile_id, activity_type)


@router.get("/active", response_model=ActivityRead | None)
def active(request: Request):
    return request.app.state.activities.get_active_session()


@router.get("/{activity_id}", response_model=ActivityRead)
def read(activity_id: str, request: Request):
    return request.app.state.activities.get(activity_id)


@router.post("/{activity_id}/cancel", response_model=ActivityRead)
async def cancel(activity_id: str, request: Request):
    return await request.app.state.activities.cancel(activity_id)
