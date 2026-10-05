from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query, Request, Response

from app.models.measurement import MeasurementRead, MeasurementUpdate

router = APIRouter(prefix="/api/v1/measurements", tags=["Measurements"])


@router.get("", response_model=list[MeasurementRead])
def list_measurements(
    request: Request,
    profile_id: Annotated[str | None, Query(alias="profileId")] = None,
    from_date: Annotated[datetime | None, Query(alias="from")] = None,
    to_date: Annotated[datetime | None, Query(alias="to")] = None,
):
    return request.app.state.measurements.list_measurements(profile_id, from_date, to_date)


@router.get("/{measurement_id}", response_model=MeasurementRead)
def get_measurement(measurement_id: str, request: Request):
    return request.app.state.measurements.get_measurement(measurement_id)


@router.patch("/{measurement_id}", response_model=MeasurementRead)
def update_measurement(measurement_id: str, values: MeasurementUpdate, request: Request):
    return request.app.state.measurements.update_measurement(measurement_id, values)


@router.delete("/{measurement_id}", status_code=204)
def delete_measurement(measurement_id: str, request: Request):
    request.app.state.measurements.delete_measurement(measurement_id)
    return Response(status_code=204)
