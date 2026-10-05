"""Validate HTTP and WebSocket inside the deployed container without weighing."""

import asyncio
import json
import os
import urllib.request

from websockets.asyncio.client import connect

PORT = os.getenv("GRAVIA_HTTP_PORT", "8080")


def request(path):
    with urllib.request.urlopen(f"http://localhost:{PORT}/api/v1/{path}", timeout=5) as response:
        return json.load(response)


async def main():
    if request("health")["status"] != "ok":
        raise RuntimeError("Healthcheck HTTP fallito.")
    board = request("board/status")
    request("activities/active")
    request("activities")
    async with asyncio.timeout(10):
        async with connect(f"ws://localhost:{PORT}/ws/live") as websocket:
            event = json.loads(await websocket.recv())
            if event["type"] not in ("board_connected", "board_disconnected"):
                raise RuntimeError("Snapshot hardware WebSocket non disponibile.")
    print(
        json.dumps(
            {
                "health": "ok",
                "websocket": "ok",
                "trainingApi": "ok",
                "boardMode": board["mode"],
                "boardConnected": board["connected"],
            }
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
