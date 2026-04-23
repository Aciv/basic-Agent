import asyncio
import sys
from typing import Dict, Optional
from IO.channel_base import InputChannel, OutputChannel, TransportMessage


class StdInChannel(InputChannel):
    """从标准输入读取行，支持中断"""
    def __init__(self, input_queue: asyncio.Queue, prompt: str = ">>> "):
        super().__init__(input_queue, name="Stdin")
        self.prompt = prompt
        self._read_task: Optional[asyncio.Future] = None  

    async def _read(self) -> TransportMessage:
        """异步读取一行（线程池方式，支持取消）"""
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
    def __init__(self, output_queue: asyncio.Queue):
        super().__init__(output_queue, name="Stdout")

    async def _write(self, data: TransportMessage):
        if data.content:
            print('system:', data.content)



async def worker(input_queue: asyncio.Queue, output_dict: Dict[str, asyncio.Queue], worker_id: int, running: asyncio.Event):
    """工作协程：增加运行标志，支持退出"""
    while running.is_set():  # 用 Event 作为退出标志
        try:
            data = await asyncio.wait_for(input_queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            continue

        if data.output_id not in output_dict.keys() or data.content is None:
            input_queue.task_done()
            continue

        '''
        # 检测退出指令（可选：输入 quit 直接退出）

        if data.content.strip().lower() == "quit":
            running.clear()  # 清除运行标志，触发所有 worker 退出
            input_queue.task_done()
            break
        '''
        response = f"[Worker-{worker_id}] 收到来自 {data.context_id}: {data.content}"
        await output_dict[data.output_id].put(TransportMessage(
            context_id=data.context_id,
            output_id=data.output_id,
            content=response
        ))
        input_queue.task_done()


async def main():
    # 创建运行标志（控制 worker 退出）
    running = asyncio.Event()
    running.set()

    # 创建队列
    input_queue = asyncio.Queue()
    output_dict = {}

    # 创建输入/输出通道
    stdin_ch = StdInChannel(input_queue, prompt="You: ")
    std_output_queue = asyncio.Queue()
    stdout_ch = StdOutChannel(std_output_queue)
    output_dict[stdout_ch.name] = std_output_queue

    # 启动通道
    stdin_ch.start()
    stdout_ch.start()

    # 启动工作协程（传入退出标志）
    workers = [asyncio.create_task(worker(input_queue, output_dict, i, running)) for i in range(2)]

    try:
        # 等待所有 worker 退出（或捕获 Ctrl+C）
        await asyncio.gather(*workers)
    except  (asyncio.CancelledError,EOFError, KeyboardInterrupt):
        print("\n检测到退出信号，正在清理资源...")
    finally:
        await stdin_ch.stop()
        await input_queue.join()

        await stdout_ch.stop()
        for o_queue in output_dict.values():
            await o_queue.join()

        for w in workers:
            if not w.done():
                w.cancel()

        await asyncio.gather(*workers, return_exceptions=True)
        print("程序已正常退出")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序强制退出")
        sys.exit(0)