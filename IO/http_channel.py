import asyncio
import uuid

from IO.channel_base import TransportMessage, InputChannel, OutputChannel
from IO.http_server import HttpServer


class HttpInChannel(InputChannel):
    def __init__(self, input_queue: asyncio.Queue,
                 server: HttpServer,
                 name: str = "HttpInput",
                 output_name: str = "HttpOutput"):
        super().__init__(input_queue=input_queue, name=name, output_name=output_name)
        self._server = server
        server.add_route("POST", "/api/chat", self._handle_chat)

    async def _handle_chat(self, request):
        body = await request.json()
        msg = body.get("message", "").strip()
        session_id = body.get("session_id", "")

        request_id = str(uuid.uuid4())
        future = asyncio.get_running_loop().create_future()
        self._server.pending[request_id] = future

        await self.input_queue.put(TransportMessage(
            context_id=session_id,
            output_id=self.output_name,
            content=msg,
            request_id=request_id
        ))

        response = await asyncio.wait_for(future, timeout=300)
        from aiohttp import web
        return web.json_response({"session_id": session_id, "response": response})

    async def _read(self):
        return None

    def start(self):
        pass


class HttpOutChannel(OutputChannel):
    def __init__(self, output_queue: asyncio.Queue,
                 server: HttpServer,
                 name: str = "HttpOutput"):
        super().__init__(output_queue=output_queue, name=name)
        self._server = server

    async def _write(self, data: TransportMessage) -> None:
        future = self._server.pending.pop(data.request_id, None)
        if future is not None and not future.done():
            future.set_result(data.content)
