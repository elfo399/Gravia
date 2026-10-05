from fastapi import APIRouter, Request

from app.models.measurement_session import SessionCreate, SessionRead

router = APIRouter(prefix="/api/v1/sessions", tags=["Sessions"])


@router.post("", response_model=SessionRead, status_code=201)
async def create_session(values: SessionCreate, request: Request):
    return await request.app.state.sessions.start_measurement_session(values.profile_id)


@router.get("/active", response_model=SessionRead | None)
def get_active_session(request: Request):
    return request.app.state.sessions.get_active_session()


@router.get("/{session_id}", response_model=SessionRead)
def get_session(session_id: str, request: Request):
    return request.app.state.sessions.get_session(session_id)


@router.post("/{session_id}/cancel", response_model=SessionRead)
async def cancel_session(session_id: str, request: Request):
    return await request.app.state.sessions.cancel_measurement_session(session_id)
