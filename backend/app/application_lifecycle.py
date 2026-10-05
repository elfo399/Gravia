import asyncio
import logging
from contextlib import asynccontextmanager

from app.balance_board.bluez_board import BluezRealBoard
from app.balance_board.calibrated_board import CalibratedBoard
from app.balance_board.demo_board import DemoBoard
from app.balance_board.real_board import RealBoard
from app.database.database import create_database_engine
from app.models.profile import ProfileCreate
from app.services.board_calibration_service import BoardCalibrationService
from app.services.measurement_service import MeasurementService
from app.services.profile_service import ProfileService
from app.services.session_service import SessionService
from app.websocket.live_measurements import LiveMeasurements


@asynccontextmanager
async def application_lifespan(app):
    settings = app.state.settings
    logging.getLogger(__name__).info("Board mode: %s", settings.board_mode)
    engine = create_database_engine(settings.database_url)
    app.state.engine = engine
    app.state.profiles = ProfileService(engine)
    app.state.measurements = MeasurementService(engine)
    app.state.live = LiveMeasurements()
    if settings.board_mode == "demo":
        board = DemoBoard()
    elif settings.board_transport == "bluez":
        board = BluezRealBoard(
            settings.board_mac, settings.board_socket, settings.board_sample_timeout
        )
    else:
        board = RealBoard(settings.board_mac, settings.board_sample_timeout)
    app.state.board = board
    app.state.sessions = SessionService(engine, board, settings, app.state.live)
    calibration = BoardCalibrationService(engine, board, app.state.sessions)
    app.state.calibration = calibration
    app.state.sessions.calibration = calibration
    if settings.board_mode == "real":
        app.state.board = CalibratedBoard(board, calibration)
        app.state.sessions.board = app.state.board
    app.state.sessions.recover_interrupted_sessions()
    if settings.demo_seed and not app.state.profiles.list_profiles():
        app.state.profiles.create_profile(ProfileCreate(name="Alfonso", height_cm=180))

    async def publish_board_status(status):
        calibration.on_board_status(status)
        status = status.model_copy(update={"calibration_active": calibration.is_active})
        await app.state.live.publish(
            {
                "type": "board_connected" if status.connected else "board_disconnected",
                "board": status.model_dump(mode="json", by_alias=True),
            }
        )

    calibration.publish_status = publish_board_status
    calibration.watchdog = asyncio.create_task(calibration.watch(), name="calibration-watchdog")
    await board.start(publish_board_status)
    try:
        yield
    finally:
        try:
            await calibration.shutdown()
            await app.state.sessions.shutdown()
        finally:
            try:
                await board.shutdown()
            finally:
                engine.dispose()
