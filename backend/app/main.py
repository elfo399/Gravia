import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.api import application, measurements, profiles, sessions
from app.api.application import serve_frontend
from app.application_lifecycle import application_lifespan
from app.configuration import Settings


def create_app(settings: Settings | None = None):
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    app = FastAPI(title="Gravia", version="0.2.0", lifespan=application_lifespan)
    app.state.settings = settings or Settings()
    for router in (application.router, profiles.router, sessions.router, measurements.router):
        app.include_router(router)

    @app.exception_handler(HTTPException)
    async def readable_http_error(request: Request, error: HTTPException):
        return JSONResponse({"message": str(error.detail)}, status_code=error.status_code)

    @app.exception_handler(RequestValidationError)
    async def readable_validation_error(request: Request, error: RequestValidationError):
        return JSONResponse(
            {
                "message": "Controlla i dati inseriti.",
                "fields": [
                    {"field": ".".join(str(part) for part in item["loc"]), "message": item["msg"]}
                    for item in error.errors()
                ],
            },
            status_code=422,
        )

    @app.exception_handler(Exception)
    async def readable_server_error(request: Request, error: Exception):
        logging.getLogger(__name__).error("Unexpected API error", exc_info=error)
        return JSONResponse(
            {"message": "Errore interno. Riprova o controlla i log di Gravia."}, status_code=500
        )

    serve_frontend(app, app.state.settings.frontend_directory)
    return app


app = create_app()
