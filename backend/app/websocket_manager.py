"""
ASTRA MIND — WebSocket Connection & Real-Time Telemetry Manager (Secured)
========================================================================
Manages authenticated live WebSocket subscriptions for astronaut and mission telemetry.

Features:
- Authenticated connection tracking (each socket mapped to authenticated user identity).
- Astronaut-specific subscription channels.
- Mission-specific subscription channels.
- Graceful disconnect cleanup and dead socket pruning.
- Real-time broadcast triggers for new PSI readings and physiological vitals.
"""

from typing import Dict, Set, Any, Optional
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger("astra_mind.websocket")


class ConnectionManager:
    """Manages active authenticated WebSocket connections and channel subscriptions."""

    def __init__(self):
        # Maps websocket -> authenticated user identity dictionary
        self.active_connections: Dict[WebSocket, Dict[str, Any]] = {}
        # Maps astronaut_id -> set of subscribed WebSockets
        self.astronaut_subscriptions: Dict[int, Set[WebSocket]] = {}
        # Maps mission_id -> set of subscribed WebSockets
        self.mission_subscriptions: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user: Dict[str, Any]):
        """Accept new authenticated WebSocket connection."""
        await websocket.accept()
        self.active_connections[websocket] = user
        logger.info(
            f"WebSocket client authenticated as {user.get('user_id')} ({user.get('role')}). Active: {len(self.active_connections)}"
        )

    def disconnect(self, websocket: WebSocket):
        """Clean up disconnected client from all subscription channels."""
        self.active_connections.pop(websocket, None)

        # Remove from astronaut channels
        for astro_id, subs in list(self.astronaut_subscriptions.items()):
            subs.discard(websocket)
            if not subs:
                self.astronaut_subscriptions.pop(astro_id, None)

        # Remove from mission channels
        for mission_id, subs in list(self.mission_subscriptions.items()):
            subs.discard(websocket)
            if not subs:
                self.mission_subscriptions.pop(mission_id, None)

        logger.info(f"WebSocket client disconnected. Remaining active: {len(self.active_connections)}")

    def get_user(self, websocket: WebSocket) -> Optional[Dict[str, Any]]:
        """Retrieve the authenticated user associated with an active socket."""
        return self.active_connections.get(websocket)

    def subscribe_astronaut(self, websocket: WebSocket, astronaut_id: int):
        """Subscribe socket to an astronaut's telemetry feed."""
        self.astronaut_subscriptions.setdefault(astronaut_id, set()).add(websocket)

    def unsubscribe_astronaut(self, websocket: WebSocket, astronaut_id: int):
        """Unsubscribe socket from astronaut channel."""
        if astronaut_id in self.astronaut_subscriptions:
            self.astronaut_subscriptions[astronaut_id].discard(websocket)

    def subscribe_mission(self, websocket: WebSocket, mission_id: int):
        """Subscribe socket to a mission's crew telemetry feed."""
        self.mission_subscriptions.setdefault(mission_id, set()).add(websocket)

    def unsubscribe_mission(self, websocket: WebSocket, mission_id: int):
        """Unsubscribe socket from mission channel."""
        if mission_id in self.mission_subscriptions:
            self.mission_subscriptions[mission_id].discard(websocket)

    async def broadcast_to_astronaut(self, astronaut_id: int, message: Dict[str, Any]):
        """Send message to all clients subscribed to astronaut_id."""
        targets = list(self.astronaut_subscriptions.get(astronaut_id, set()))
        dead_sockets = []
        payload = json.dumps(message)
        for ws in targets:
            try:
                await ws.send_text(payload)
            except Exception:
                dead_sockets.append(ws)

        for dead in dead_sockets:
            self.disconnect(dead)

    async def broadcast_to_mission(self, mission_id: int, message: Dict[str, Any]):
        """Send message to all clients subscribed to mission_id."""
        targets = list(self.mission_subscriptions.get(mission_id, set()))
        dead_sockets = []
        payload = json.dumps(message)
        for ws in targets:
            try:
                await ws.send_text(payload)
            except Exception:
                dead_sockets.append(ws)

        for dead in dead_sockets:
            self.disconnect(dead)

    async def broadcast_all(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients."""
        payload = json.dumps(message)
        dead_sockets = []
        for ws in list(self.active_connections.keys()):
            try:
                await ws.send_text(payload)
            except Exception:
                dead_sockets.append(ws)

        for dead in dead_sockets:
            self.disconnect(dead)


# Global singleton connection manager
ws_manager = ConnectionManager()
