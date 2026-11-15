"""
ASTRA MIND — Real-Time WebSocket Telemetry Streaming Router (Secured)
=====================================================================
Provides authenticated, role-authorized bi-directional telemetry feeds.

SECURITY & ACCESS RULES (SEC-02):
- Requires authentication token via query param (?token=... / ?api_key=...) or X-API-Key header.
- Unauthenticated or invalid connections are closed with code 1008 Policy Violation.
- Client identity is strictly derived from the authenticated token, NEVER from client-supplied IDs.
- Astronauts can subscribe ONLY to their own telemetry stream.
- Flight surgeons and mission directors can subscribe to authorized astronaut and mission feeds.
- Unauthorized subscription attempts are rejected safely without disconnecting the client.
"""

import json
import logging
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .websocket_manager import ws_manager
from .security import verify_token

logger = logging.getLogger("astra_mind.ws_router")

router = APIRouter(prefix="/ws", tags=["Real-Time WebSockets"])


@router.websocket("/telemetry")
async def websocket_telemetry_endpoint(
    websocket: WebSocket,
    token: Optional[str] = None,
    api_key: Optional[str] = None,
    astronaut_id: Optional[int] = None,
    mission_id: Optional[int] = None,
):
    """
    WebSocket streaming endpoint for real-time astronaut and mission telemetry.
    Authenticates connection before accepting subscriptions.
    """
    # 1. Resolve authentication token from query parameter or headers
    resolved_token = token or api_key or websocket.headers.get("x-api-key")
    if not resolved_token:
        auth_header = websocket.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            resolved_token = auth_header.split(" ", 1)[1].strip()

    # 2. Verify token
    user = verify_token(resolved_token) if resolved_token else None
    if not user:
        # Reject unauthenticated connection with WS close code 1008 (Policy Violation)
        await websocket.close(code=1008, reason="Missing or invalid authentication credentials")
        return

    # 3. Accept authenticated connection and track user identity
    await ws_manager.connect(websocket, user=user)

    # 4. Process initial subscriptions if provided in query parameters with role authorization
    if astronaut_id is not None:
        target_astro = int(astronaut_id)
        if user["role"] in ["flight_surgeon", "mission_director"] or (
            user["role"] == "astronaut" and user.get("astronaut_id") == target_astro
        ):
            ws_manager.subscribe_astronaut(websocket, target_astro)
            await websocket.send_text(json.dumps({
                "type": "subscribed",
                "channel": "astronaut",
                "id": target_astro,
            }))
        else:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Unauthorized subscription: astronaut {user.get('astronaut_id')} cannot subscribe to astronaut {target_astro}.",
            }))

    if mission_id is not None:
        target_mission = int(mission_id)
        if user["role"] in ["flight_surgeon", "mission_director"]:
            ws_manager.subscribe_mission(websocket, target_mission)
            await websocket.send_text(json.dumps({
                "type": "subscribed",
                "channel": "mission",
                "id": target_mission,
            }))
        else:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Unauthorized subscription: role '{user['role']}' cannot subscribe to mission streams.",
            }))

    # 5. In-flight command message processing loop
    try:
        while True:
            raw_msg = await websocket.receive_text()
            try:
                msg = json.loads(raw_msg)
            except Exception:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Malformed JSON payload",
                }))
                continue

            action = msg.get("action")

            if action == "subscribe_astronaut":
                target_id = msg.get("astronaut_id")
                if target_id is not None:
                    try:
                        target_astro = int(target_id)
                    except ValueError:
                        await websocket.send_text(json.dumps({"type": "error", "message": "Invalid astronaut_id"}))
                        continue

                    # Role-based subscription authorization
                    if user["role"] in ["flight_surgeon", "mission_director"] or (
                        user["role"] == "astronaut" and user.get("astronaut_id") == target_astro
                    ):
                        ws_manager.subscribe_astronaut(websocket, target_astro)
                        await websocket.send_text(json.dumps({
                            "type": "subscribed",
                            "channel": "astronaut",
                            "id": target_astro,
                        }))
                    else:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": f"Unauthorized subscription: astronaut {user.get('astronaut_id')} cannot subscribe to astronaut {target_astro}.",
                        }))

            elif action == "unsubscribe_astronaut":
                target_id = msg.get("astronaut_id")
                if target_id is not None:
                    ws_manager.unsubscribe_astronaut(websocket, int(target_id))
                    await websocket.send_text(json.dumps({
                        "type": "unsubscribed",
                        "channel": "astronaut",
                        "id": int(target_id),
                    }))

            elif action == "subscribe_mission":
                target_id = msg.get("mission_id")
                if target_id is not None:
                    try:
                        target_mission = int(target_id)
                    except ValueError:
                        await websocket.send_text(json.dumps({"type": "error", "message": "Invalid mission_id"}))
                        continue

                    # Role-based mission subscription authorization
                    if user["role"] in ["flight_surgeon", "mission_director"]:
                        ws_manager.subscribe_mission(websocket, target_mission)
                        await websocket.send_text(json.dumps({
                            "type": "subscribed",
                            "channel": "mission",
                            "id": target_mission,
                        }))
                    else:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": f"Unauthorized subscription: role '{user['role']}' cannot subscribe to mission streams.",
                        }))

            elif action == "unsubscribe_mission":
                target_id = msg.get("mission_id")
                if target_id is not None:
                    ws_manager.unsubscribe_mission(websocket, int(target_id))
                    await websocket.send_text(json.dumps({
                        "type": "unsubscribed",
                        "channel": "mission",
                        "id": int(target_id),
                    }))

            elif action == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

            else:
                await websocket.send_text(json.dumps({
                    "type": "unknown_action",
                    "action": action,
                }))

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info("WebSocket client disconnected gracefully.")
    except Exception as e:
        ws_manager.disconnect(websocket)
        logger.error(f"WebSocket unhandled error: {str(e)}")
