import asyncio

from fastapi import WebSocket


class LiveMeasurements:
    def __init__(self):
        self.connections: set[WebSocket] = set()
        self.latest_status: dict | None = None
        self.latest_reading: dict | None = None
        self.latest_completion: dict | None = None
        self.latest_board_status: dict | None = None
        self.latest_activity_status: dict | None = None
        self.latest_activity_reading: dict | None = None
        self.latest_activity_completion: dict | None = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.add(websocket)
        for event in (
            self.latest_board_status,
            self.latest_status,
            self.latest_reading,
            self.latest_completion,
            self.latest_activity_status,
            self.latest_activity_reading,
            self.latest_activity_completion,
        ):
            if event:
                await websocket.send_json(event)

    async def publish(self, event: dict):
        if event["type"] in ("board_connected", "board_disconnected"):
            self.latest_board_status = event
        elif event["type"] == "session_status":
            self.latest_status = event
            if event["status"] == "WAITING_FOR_USER":
                self.latest_reading = None
                self.latest_completion = None
        elif event["type"] == "live_measurement":
            self.latest_reading = event
        elif event["type"] == "measurement_completed":
            self.latest_completion = event
        elif event["type"] == "activity_status":
            self.latest_activity_status = event
            if event["status"] == "WAITING_FOR_USER":
                self.latest_activity_reading = None
                self.latest_activity_completion = None
            if event["status"] in ("ERROR", "CANCELLED"):
                self.latest_activity_reading = None
        elif event["type"] == "activity_live":
            self.latest_activity_reading = event
        elif event["type"] == "activity_completed":
            self.latest_activity_completion = event

        async def send(connection):
            try:
                await asyncio.wait_for(connection.send_json(event), timeout=1)
            except Exception:
                self.connections.discard(connection)

        await asyncio.gather(*(send(connection) for connection in tuple(self.connections)))
