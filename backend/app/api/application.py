from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from sqlmodel import Session, text

from app.models.board_status import BoardStatus

router = APIRouter()


@router.get("/api/v1/health")
def health(request: Request):
    with Session(request.app.state.engine) as db:
        db.exec(text("SELECT 1"))
    return {"status": "ok", "version": "0.2.0"}


@router.get("/api/v1/board/status", response_model=BoardStatus)
def board_status(request: Request):
    return request.app.state.board.get_status()


@router.get("/api/v1/settings")
def settings(request: Request):
    config = request.app.state.settings
    return {
        "boardMode": config.board_mode,
        "minimumWeight": config.minimum_weight,
        "requiredStability": config.required_stability,
        "stableDuration": config.stable_duration,
        "sessionTimeout": config.session_timeout,
    }


@router.websocket("/ws/live")
async def live_measurements(websocket: WebSocket):
    live = websocket.app.state.live
    try:
        await live.connect(websocket)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        live.connections.discard(websocket)


def serve_frontend(app, directory: str):
    root = Path(directory).resolve()
    if not (root / "index.html").exists():
        return

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path.startswith(("api/", "ws/")):
            raise HTTPException(404, "Endpoint non trovato.")
        requested = (root / path).resolve()
        if not requested.is_relative_to(root):
            raise HTTPException(404, "Risorsa non trovata.")
        return FileResponse(requested if requested.is_file() else root / "index.html")
