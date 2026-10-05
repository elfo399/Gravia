import logging
from contextlib import asynccontextmanager

from app.balance_board.demo_board import DemoBoard
from app.balance_board.real_board import RealBoard
from app.database.database import create_database_engine
from app.models.profile import ProfileCreate
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
    board = (
        DemoBoard()
        if settings.board_mode == "demo"
        else RealBoard(settings.board_mac, settings.board_sample_timeout)
    )
    app.state.board = board
    app.state.sessions = SessionService(engine, board, settings, app.state.live)
    app.state.sessions.recover_interrupted_sessions()
    if settings.demo_seed and not app.state.profiles.list_profiles():
        app.state.profiles.create_profile(ProfileCreate(name="Alfonso", height_cm=180))

    async def publish_board_status(status):
        await app.state.live.publish(
            {
                "type": "board_connected" if status.connected else "board_disconnected",
                "board": status.model_dump(mode="json", by_alias=True),
            }
        )

    await board.start(publish_board_status)
    try:
        yield
    finally:
        try:
            await app.state.sessions.shutdown()
        finally:
            try:
                await board.shutdown()
            finally:
                engine.dispose()
