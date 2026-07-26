import asyncio
import json
import websockets
from websockets.server import serve
from src.config.settings import Config

_CONNECTED_CLIENTS = set()
_MESSAGE_CACHE = {}

async def register(websocket):
    _CONNECTED_CLIENTS.add(websocket)
    
    # Send cached messages immediately upon connection
    for msg_type, msg_str in _MESSAGE_CACHE.items():
        try:
            await websocket.send(msg_str)
        except Exception:
            pass

    try:
        await websocket.wait_closed()
    finally:
        _CONNECTED_CLIENTS.remove(websocket)

async def broadcast_message(message: dict):
    """
    Broadcast a JSON message to all connected clients.
    """
    if "type" in message:
        message_str = json.dumps(message)
        _MESSAGE_CACHE[message["type"]] = message_str
        
        if _CONNECTED_CLIENTS:
            await asyncio.gather(
                *[asyncio.create_task(client.send(message_str)) for client in _CONNECTED_CLIENTS],
                return_exceptions=True
            )

async def start_websocket_server(config: Config):
    """
    Start the WebSocket server on the configured host and port.
    This coroutine will block and run the server indefinitely.
    """
    host = config.websocket.host
    port = config.websocket.port
    
    async with serve(register, host, port):
        # Run forever
        await asyncio.Future()
