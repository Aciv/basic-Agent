import asyncio
from typing import Dict, Callable, Awaitable

try:
    from aiohttp import web
except ImportError:
    web = None


class HttpServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.pending: Dict[str, asyncio.Future] = {}
        self._app = web.Application() if web else None
        self._runner = None
        self._site = None

    def add_route(self, method: str, path: str, handler):
        if method.upper() == "GET":
            self._app.router.add_get(path, handler)
        elif method.upper() == "POST":
            self._app.router.add_post(path, handler)

    def add_static(self, path: str, file_path: str):
        async def handler(request):
            return web.FileResponse(file_path)
        self._app.router.add_get(path, handler)

    async def start(self):
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self.host, self.port)
        await self._site.start()
        print(f"Server started on http://{self.host}:{self.port}")

    async def stop(self):
        if self._site:
            await self._site.stop()
        if self._runner:
            await self._runner.cleanup()
