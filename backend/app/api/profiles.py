from fastapi import APIRouter, Request, Response

from app.models.profile import ProfileCreate, ProfileRead, ProfileUpdate

router = APIRouter(prefix="/api/v1/profiles", tags=["Profiles"])


@router.get("", response_model=list[ProfileRead])
def list_profiles(request: Request):
    return request.app.state.profiles.list_profiles()


@router.post("", response_model=ProfileRead, status_code=201)
def create_profile(values: ProfileCreate, request: Request):
    return request.app.state.profiles.create_profile(values)


@router.get("/{profile_id}", response_model=ProfileRead)
def get_profile(profile_id: str, request: Request):
    return request.app.state.profiles.get_profile(profile_id)


@router.patch("/{profile_id}", response_model=ProfileRead)
def update_profile(profile_id: str, values: ProfileUpdate, request: Request):
    return request.app.state.profiles.update_profile(profile_id, values)


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: str, request: Request):
    request.app.state.profiles.delete_profile(profile_id)
    return Response(status_code=204)
