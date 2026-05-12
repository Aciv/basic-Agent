import heapq
import time
import asyncio
from typing import Callable, Optional
import queue

from IO.channel_base import TransportMessage

class MinHeapTimer:
    def __init__(self, input_queue: asyncio.Queue):
        self._input_queue = input_queue

        # 堆: (执行时间, 任务名称，序列号, TransportMessage)
        self._task_queue = []          
        self._task_counter = 0
        self._condition = asyncio.Condition()
        self._running = False
        self.next_tick = 0

        # 用于记录被取消的任务 ID（线程安全由 _condition 保护）
        self._cancelled_ids = set()

    async def add_task(self, delay: float, task_name: str, message: TransportMessage) -> int:
        execute_time = time.time() + delay
        async with self._condition:
            task_id = self._task_counter
            self._task_counter += 1

            old_top_time = self._task_queue[0][0] if self._task_queue else None
            heapq.heappush(
                self._task_queue,
                (execute_time, task_name, task_id, message)
            )
            if old_top_time is None or execute_time < old_top_time:
                self._condition.notify()
        return task_id

    async def cancel_task(self, task_id: int) -> bool:
        async with self._condition:
            # 简单的 ID 范围检查，防止无效 ID 污染集合
            if task_id < 0 or task_id >= self._task_counter:
                return False
            self._cancelled_ids.add(task_id)
            return True

    async def run(self):
        self._running = True
        while self._running:
            task_to_send = None
            async with self._condition:
            
                # 堆为空：等待新任务加入
                if not self._task_queue:
                    await self._condition.wait()   
                    continue
                # print("wtf")
                execute_time, _, task_id, message = self._task_queue[0]
                now = time.time()

                if now >= execute_time:
                    heapq.heappop(self._task_queue)
                    if task_id in self._cancelled_ids:
                        self._cancelled_ids.discard(task_id)
                        continue
                    task_to_send = message

                    self.next_tick = 0
                else:
                    self.next_tick = execute_time - now
                    try:
                        await asyncio.wait_for(self._condition.wait(), timeout=self.next_tick)
                    except asyncio.TimeoutError:
                        pass
                    
            if task_to_send is not None:
                await self._input_queue.put(task_to_send)

    def get_info(self):
        return self._task_queue.copy()
    
    async def stop(self):
        async with self._condition:
            self._running = False
            self._condition.notify()

            
# 全局定时器实例
_timer_instance: Optional[MinHeapTimer] = None


def get_timer(input_queue: Optional[asyncio.Queue] = None) -> MinHeapTimer:
    """获取全局定时器实例"""
    global _timer_instance
    if _timer_instance is None:
        _timer_instance = MinHeapTimer(input_queue)
    return _timer_instance