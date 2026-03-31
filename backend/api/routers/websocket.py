"""WebSocket endpoints for real-time data streaming."""

import asyncio
import json
import logging
from typing import List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            f"WebSocket connected. Total connections: {len(self.active_connections)}"
        )

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(
            f"WebSocket disconnected. Total connections: {len(self.active_connections)}"
        )

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific WebSocket."""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        """Broadcast a message to all connected WebSockets."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)


# Global connection manager instance
manager = ConnectionManager()


@router.websocket("/prices")
async def websocket_prices(websocket: WebSocket):
    """WebSocket endpoint for real-time price updates."""
    await manager.connect(websocket)

    try:
        # Send initial connection confirmation
        await websocket.send_text(
            json.dumps(
                {
                    "type": "connection",
                    "status": "connected",
                    "message": "Real-time price feed connected",
                }
            )
        )

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for client messages (ping, subscribe requests, etc.)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                message = json.loads(data)

                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                elif message.get("type") == "subscribe":
                    # Handle subscription to specific symbols
                    symbols = message.get("symbols", [])
                    await websocket.send_text(
                        json.dumps({"type": "subscribed", "symbols": symbols})
                    )

            except asyncio.TimeoutError:
                # Send periodic heartbeat
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "heartbeat",
                            "timestamp": asyncio.get_event_loop().time(),
                        }
                    )
                )
            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({"type": "error", "message": "Invalid JSON format"})
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@router.websocket("/backtest-progress/{task_id}")
async def websocket_backtest_progress(websocket: WebSocket, task_id: str):
    """
    DEPRECATED: WebSocket endpoint for real-time backtest progress.
    Celery removed - GitHub Actions handles scheduling.
    """
    await manager.connect(websocket)

    try:
        # REMOVED: Celery task monitoring
        await websocket.send_text(
            json.dumps(
                {
                    "type": "error",
                    "message": "Async backtest monitoring removed. Celery infrastructure deprecated.",
                }
            )
        )
        await websocket.close()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Backtest WebSocket error: {e}")
        manager.disconnect(websocket)


async def broadcast_price_update(symbol: str, price_data: dict):
    """Utility function to broadcast price updates to all connected clients."""
    message = json.dumps(
        {
            "type": "price_update",
            "symbol": symbol,
            "data": price_data,
            "timestamp": asyncio.get_event_loop().time(),
        }
    )
    await manager.broadcast(message)


async def broadcast_correlation_update(correlation_data: dict):
    """Utility function to broadcast correlation matrix updates."""
    message = json.dumps(
        {
            "type": "correlation_update",
            "data": correlation_data,
            "timestamp": asyncio.get_event_loop().time(),
        }
    )
    await manager.broadcast(message)
