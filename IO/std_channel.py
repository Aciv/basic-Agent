import asyncio
from typing import Optional
from IO.channel_base import InputChannel, OutputChannel, TransportMessage


class StdInChannel(InputChannel):
    def __init__(self, input_queue: asyncio.Queue, 
                output_name: Optional[str] = "Stdout", error_name: Optional[str] = "Stdout", name: str = "Stdin",
                prompt: str = ">>> ", semaphore: Optional[asyncio.Semaphore] = None):
        super().__init__(input_queue=input_queue, output_name=output_name,
                         name=name, 
                         error_name=error_name,
                         semaphore=semaphore)
        self.prompt = prompt
        self._read_task: Optional[asyncio.Future] = None  


    async def _read(self) -> TransportMessage:
        loop = asyncio.get_running_loop()
        try:
            self._read_task = loop.run_in_executor(None, input, self.prompt)
            line = await self._read_task
            if line == "" or line is None:
                return None
            
            return TransportMessage(
                context_id=self.name,
                output_id=self.output_name,
                content=line.rstrip("\n")
            )
        except (asyncio.CancelledError,EOFError, KeyboardInterrupt):
            if self._read_task and not self._read_task.done():
                self._read_task.cancel()
            raise
        except Exception as e:
            raise

        finally:
            self._read_task = None

    async def stop(self):
        if self._read_task and not self._read_task.done():
            self._read_task.cancel()
        await super().stop()

class StdOutChannel(OutputChannel):
    def __init__(self, output_queue: asyncio.Queue, name: Optional[str] = "Stdout",
                 semaphore: Optional[asyncio.Semaphore] = None):
        super().__init__(output_queue=output_queue, name=name,
                        semaphore=semaphore)

    async def _write(self, data: TransportMessage):
        if data.content:
            print('system:', data.content)



