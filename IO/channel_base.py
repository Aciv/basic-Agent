import asyncio
import sys
from abc import ABC, abstractmethod
from typing import Any, Optional

from dataclasses import dataclass, field

@dataclass
class TransportMessage:
    """工具信息类"""
    context_id: str
    output_id: str
    content: Optional[str] = None



class InputChannel(ABC):
    """输入通道基类：从某个数据源读取原始数据，放入输入队列"""

    def __init__(self, input_queue: asyncio.Queue, output_name: Optional[str] = "Stdout", error_name: Optional[str] = "Stdout", name: str = "InputChannel", ):
        self.input_queue = input_queue
        self.name = name
        self.output_name = output_name
        self.error_output = error_name

        self._task: Optional[asyncio.Task] = None
        self._running = False

    @abstractmethod
    async def _read(self) -> TransportMessage:
        raise NotImplementedError

    async def _run(self):
        while self._running:
            try:
                data = await self._read()
                if data is None:          
                    continue
                await self.input_queue.put(data)
            except (asyncio.CancelledError,EOFError, KeyboardInterrupt):
                self._running = False
            except Exception as e:
                await self.input_queue.put(TransportMessage(
                        context_id=self.name,
                        output_id=self.error_output,
                        content=str(e)))

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
    """输出通道基类：从输出队列取出消息并输出到目标"""

    def __init__(self, output_queue: asyncio.Queue, name: str = "OutputChannel"):
        self.output_queue = output_queue
        self.name = name
        self._task: Optional[asyncio.Task] = None
        self._running = False

    @abstractmethod
    async def _write(self, data: Any) -> None:
        raise NotImplementedError

    async def _run(self):
        while self._running:
            try:
                # 超时设置让停止时能及时退出
                msg = await asyncio.wait_for(self.output_queue.get(), timeout=0.1)
                
                await self._write(msg)
                self.output_queue.task_done()
            except asyncio.TimeoutError:
                continue
            except (asyncio.CancelledError,EOFError, KeyboardInterrupt):
                self._running = False
            except Exception as e:
                print(f"[{self.name}] 输出错误: {e}", file=sys.stderr)

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





