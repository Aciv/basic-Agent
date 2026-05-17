import asyncio
import uuid
import json

from IO.channel_base import TransportMessage, InputChannel, OutputChannel
from aiohttp import web


class WsServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8082):
        self.host = host
        self.port = port
        self.connections: dict[str, web.WebSocketResponse] = {}
        self._app = web.Application()
        self._runner = None
        self._site = None

    def add_static(self, path: str, file_path: str):
        async def handler(request):
            return web.FileResponse(file_path)
        self._app.router.add_get(path, handler)

    async def start(self):
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self.host, self.port)
        await self._site.start()
        print(f"WebSocket Server started on ws://{self.host}:{self.port}")

    async def stop(self):
        if self._site:
            await self._site.stop()
        if self._runner:
            await self._runner.cleanup()


class WsInChannel(InputChannel):
    def __init__(self, input_queue: asyncio.Queue,
                 server: WsServer,
                 name: str = "WsInput",
                 output_name: str = "WsOutput"):
        super().__init__(input_queue=input_queue, name=name, output_name=output_name)
        self._server = server
        server._app.router.add_get("/api/ws", self._handle_ws)

    async def _handle_ws(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        session_id = request.query.get("session_id", str(uuid.uuid4()))
        self._server.connections[session_id] = ws

        print(f"[WS] Client connected: session={session_id}")
        await ws.send_json({"type": "connected", "session_id": session_id})

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                    except json.JSONDecodeError as e:
                        print(f"[WS] Invalid JSON from {session_id}: {e}")
                        continue
                    message = data.get("message", "").strip()

                    await self.input_queue.put(TransportMessage(
                        context_id=session_id,
                        output_id=self.output_name,
                        content=message
                    ))
                elif msg.type == web.WSMsgType.ERROR:
                    print(f"[WS] Error: {ws.exception()}")
        except (asyncio.CancelledError, ConnectionResetError, ConnectionAbortedError):
            pass
        finally:
            self._server.connections.pop(session_id, None)
            print(f"[WS] Client disconnected: session={session_id}")

        return ws

    async def _read(self):
        return None

    def start(self):
        pass


class WsOutChannel(OutputChannel):
    def __init__(self, output_queue: asyncio.Queue,
                 server: WsServer,
                 name: str = "WsOutput"):
        super().__init__(output_queue=output_queue, name=name)
        self._server = server

    async def _write(self, data: TransportMessage) -> None:
        ws = self._server.connections.get(data.context_id)
        if ws is not None and not ws.closed:
            try:
                await ws.send_json({"response": data.content})
            except (ConnectionResetError, ConnectionAbortedError):
                pass
        else:
            print(f"[WS] WARNING: No connection for session={data.context_id}")
