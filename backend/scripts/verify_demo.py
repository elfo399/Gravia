"""Exercise the actual REST + WebSocket demo, preserving the completed measurement."""

import asyncio
import json
import urllib.request

from websockets.asyncio.client import connect


def request(path, body=None, method=None):
    encoded = json.dumps(body).encode() if body is not None else None
    http_request = urllib.request.Request(
        f"http://localhost:8080{path}",
        data=encoded,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(http_request, timeout=5) as response:
        return json.load(response)


async def verify_demo():
    assert request("/api/v1/health")["status"] == "ok"
    profiles = request("/api/v1/profiles")
    assert profiles
    profile_id = profiles[0]["id"]
    statuses = []
    weights = []
    async with connect("ws://localhost:8080/ws/live") as websocket:
        session = request("/api/v1/sessions", {"profileId": profile_id})
        async with asyncio.timeout(30):
            async for raw in websocket:
                event = json.loads(raw)
                if event.get("sessionId") != session["id"]:
                    continue
                if event["type"] == "session_status":
                    statuses.append(event["status"])
                if event["type"] == "live_measurement":
                    weights.append(event["weight"])
                    assert abs(sum(event["sensors"].values()) - event["weight"]) < 0.002
                    assert -1 <= event["centerOfPressure"]["x"] <= 1
                    assert -1 <= event["centerOfPressure"]["y"] <= 1
                if event["type"] == "error":
                    raise AssertionError(event["message"])
                if event["type"] == "measurement_completed":
                    measurement = event["measurement"]
                    break
    assert statuses == ["WAITING_FOR_USER", "MEASURING", "STABILIZING", "COMPLETED"], statuses
    assert len(weights) > 30 and min(weights) == 0 and max(weights) > 70
    assert measurement["stability"] >= 95
    assert measurement["measuredAt"].endswith("Z")
    saved = request(f"/api/v1/measurements/{measurement['id']}")
    assert saved["sessionId"] == session["id"]
    history = request(f"/api/v1/measurements?profileId={profile_id}")
    assert any(item["id"] == saved["id"] for item in history)
    print(
        json.dumps(
            {
                "result": "passed",
                "statuses": statuses,
                "liveSamples": len(weights),
                "measurementId": saved["id"],
                "weight": saved["weight"],
            }
        )
    )


if __name__ == "__main__":
    asyncio.run(verify_demo())
