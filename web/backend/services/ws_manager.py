import asyncio
import json
import logging
from typing import Dict, List, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    WebSocket connection manager for real-time progress updates.
    
    Supports:
    - Per-task connection grouping (clients subscribe to specific task_id)
    - Thread-safe broadcast from sync TaskManager callbacks
    - Auto-cleanup on disconnect
    """

    def __init__(self):
        self._connections: Dict[int, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, task_id: int):
        await websocket.accept()
        async with self._lock:
            if task_id not in self._connections:
                self._connections[task_id] = set()
            self._connections[task_id].add(websocket)
        logger.info(f"WebSocket connected for task {task_id}. Total connections: {len(self._connections.get(task_id, set()))}")

    async def disconnect(self, websocket: WebSocket, task_id: int):
        async with self._lock:
            if task_id in self._connections:
                self._connections[task_id].discard(websocket)
                if not self._connections[task_id]:
                    del self._connections[task_id]
        logger.info(f"WebSocket disconnected for task {task_id}")

    async def broadcast_to_task(self, task_id: int, data: dict):
        async with self._lock:
            connections = list(self._connections.get(task_id, set()))

        if not connections:
            return

        message = json.dumps(data, default=str)
        disconnected = []

        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket for task {task_id}: {e}")
                disconnected.append(ws)

        if disconnected:
            async with self._lock:
                for ws in disconnected:
                    if task_id in self._connections:
                        self._connections[task_id].discard(ws)
                        if not self._connections[task_id]:
                            del self._connections[task_id]

    def broadcast_sync(self, task_id: int, data: dict):
        """
        Thread-safe sync wrapper for broadcasting from TaskManager's worker threads.
        Creates a new event loop or uses the running one to schedule the broadcast.
        """
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast_to_task(task_id, data))
        except RuntimeError:
            try:
                asyncio.run(self.broadcast_to_task(task_id, data))
            except Exception as e:
                logger.error(f"Failed to broadcast progress for task {task_id}: {e}")

    def get_connection_count(self, task_id: int) -> int:
        return len(self._connections.get(task_id, set()))

    def get_total_connections(self) -> int:
        return sum(len(conns) for conns in self._connections.values())


ws_manager = ConnectionManager()
