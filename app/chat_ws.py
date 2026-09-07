"""
app/chat_ws.py

A tiny in-process WebSocket connection registry for the chat feature.
Keeps a set of live WebSocket connections per username (a user can have
several — multiple browser tabs/devices) so the REST endpoints in
app/routers/chat.py can push events (new message, edited/deleted message,
group updates, typing indicators, read receipts) to whoever's online,
instead of making every client poll.

Deliberately process-local, same documented limitation as storage.py's
threading lock: fine for a single-instance deployment (Render
free/starter tier), not for a multi-instance/horizontally-scaled one —
that would need a pub/sub backend (Redis etc.) instead.
"""
import logging

from fastapi import WebSocket

logger = logging.getLogger("gt.chat_ws")


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}

    async def connect(self, username: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(username, set()).add(websocket)

    def disconnect(self, username: str, websocket: WebSocket) -> None:
        conns = self._connections.get(username)
        if not conns:
            return
        conns.discard(websocket)
        if not conns:
            self._connections.pop(username, None)

    def is_online(self, username: str) -> bool:
        return bool(self._connections.get(username))

    async def send_to_user(self, username: str, payload: dict) -> None:
        for ws in list(self._connections.get(username, ())):
            try:
                await ws.send_json(payload)
            except Exception:
                logger.info("Dropping dead chat socket for %s", username)
                self.disconnect(username, ws)

    async def broadcast(self, usernames, payload: dict) -> None:
        for username in usernames:
            await self.send_to_user(username, payload)


manager = ConnectionManager()
