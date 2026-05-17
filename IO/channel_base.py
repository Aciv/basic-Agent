import asyncio
import sys
from abc import ABC, abstractmethod
from typing import Any, Optional

from dataclasses import dataclass, field

@dataclass
class TransportMessage:
    context_id: str
    output_id: str
    content: Optional[str] = None
    request_id: str = ""



class InputChannel(ABC):
    def __init__(self, input_queue: asyncio.Queue, 
                output_name: Optional[str] = "Stdout", 
                error_name: Optional[str] = "Stdout", 
                name: str = "InputChannel",
                semaphore: Optional[asyncio.Semaphore] = None,
                poll_interval: Optional[float] = None):
        """
        :param poll_interval: 轮询间隔（秒）。为 None 时表示阻塞读取（如 stdin），
                               有值时表示非阻塞轮询，无消息时等待指定间隔再重试。
        """
        self.input_queue = input_queue
        self.name = name
        self.output_name = output_name
        self.error_output = error_name

        self.semaphore = semaphore
        self.poll_interval = poll_interval

        self._task: Optional[asyncio.Task] = None
        self._running = False

    @abstractmethod
    async def _read(self) -> Optional[TransportMessage]:
        """
        从数据源读取一条消息。
        返回 None 表示暂无消息（轮询模式下会等待 poll_interval 后重试）。
        """
        raise NotImplementedError

    async def _run(self):
        while self._running:
            try:
                data = await self._read()
                if data is None:
                    if self.poll_interval is not None:
                        await asyncio.sleep(self.poll_interval)
                    continue

                await self.input_queue.put(data)
                
                if self.semaphore is not None:
                    await self.semaphore.acquire()
            except (asyncio.CancelledError,EOFError, KeyboardInterrupt):
                self._running = False
            except Exception as e:
                await self.input_queue.put(TransportMessage(
                        context_id=self.name,
                        output_id=self.error_output,
                        content=str(e)))
                
    def get_name(self) -> str:
        return self.name
    def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            await self._task



class OutputChannel(ABC):
    def __init__(self, output_queue: asyncio.Queue, name: str = "OutputChannel",
                 semaphore: Optional[asyncio.Semaphore] = None):
        self.output_queue = output_queue
        self.name = name
        self.semaphore = semaphore
        self._task: Optional[asyncio.Task] = None
        self._running = False
        
    @abstractmethod
    async def _write(self, data: Any) -> None:
        raise NotImplementedError

    async def _run(self):
        while self._running:
            try:
                msg = await asyncio.wait_for(self.output_queue.get(), timeout=0.1)
                
                await self._write(msg)
                self.output_queue.task_done()
                if self.semaphore is not None and msg.output_id == self.name:
                    self.semaphore.release()

            except asyncio.TimeoutError:
                continue
            except (asyncio.CancelledError,EOFError, KeyboardInterrupt):
                self._running = False
            except Exception as e:
                print(f"[{self.name}] 输出错误: {e}", file=sys.stderr)

    def get_name(self) -> str:
        return self.name
    
    def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            await self._task





