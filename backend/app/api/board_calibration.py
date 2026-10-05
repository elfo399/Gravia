from fastapi import APIRouter, Request

from app.models.board_calibration import (
    BoardCalibrationStatus,
    CalibrationCommand,
    CalibrationSessionRead,
    ReferenceWeight,
)

router = APIRouter(prefix="/api/v1/board/calibration", tags=["Board calibration"])


@router.get("", response_model=BoardCalibrationStatus)
async def calibration(request: Request):
    return request.app.state.calibration.read()


@router.delete("", response_model=BoardCalibrationStatus)
async def reset(request: Request):
    return await request.app.state.calibration.reset()


@router.post("/session", response_model=CalibrationSessionRead, status_code=201)
async def start(request: Request, command: CalibrationCommand | None = None):
    return await request.app.state.calibration.start()


@router.get("/session/{identifier}", response_model=CalibrationSessionRead)
async def session(identifier: str, request: Request):
    return request.app.state.calibration._session(identifier).result.model_copy()


@router.delete("/session/{identifier}", status_code=204)
async def cancel(identifier: str, request: Request):
    await request.app.state.calibration.cancel(identifier)


@router.post("/session/{identifier}/tare", response_model=CalibrationSessionRead)
async def tare(identifier: str, request: Request, command: CalibrationCommand | None = None):
    return await request.app.state.calibration.acquire(identifier, "tare")


@router.post("/session/{identifier}/reference", response_model=CalibrationSessionRead)
async def reference(identifier: str, values: ReferenceWeight, request: Request):
    return await request.app.state.calibration.acquire(
        identifier, "reference", values.reference_weight
    )


@router.post("/session/{identifier}/verify", response_model=CalibrationSessionRead)
async def verify(identifier: str, request: Request, command: CalibrationCommand | None = None):
    return await request.app.state.calibration.acquire(identifier, "verify")


@router.post("/session/{identifier}/save", response_model=BoardCalibrationStatus)
async def save(identifier: str, request: Request, command: CalibrationCommand | None = None):
    return await request.app.state.calibration.save(identifier)
