import heapq
import time
import threading
from typing import Callable, Optional
import queue


class MinHeapTimer:
    def __init__(self):
        self._task_queue = []          # 堆: (执行时间, 任务名称，序列号, 回调, args, kwargs)
        self.ready_queue = queue.Queue()
        self._task_counter = 0
        self._condition = threading.Condition()
        self._running = False
        self.next_tick = -1

        # 新增：用于记录被取消的任务 ID（线程安全由 _condition 保护）
        self._cancelled_ids = set()

    def add_task(self, delay: float, task_name: str, callback: Callable, *args, **kwargs) -> int:
        """
        添加定时任务，返回唯一的 task_id，可用于取消。
        """
        execute_time = time.time() + delay
        with self._condition:
            task_id = self._task_counter
            self._task_counter += 1

            old_top_time = self._task_queue[0][0] if self._task_queue else None
            heapq.heappush(
                self._task_queue,
                (execute_time, task_name, task_id, callback, args, kwargs)
            )
            if old_top_time is None or execute_time < old_top_time:
                self._condition.notify()
        return task_id

    def cancel_task(self, task_id: int) -> bool:
        """
        取消指定 task_id 的任务。
        返回 True 表示成功标记为取消（无论任务是否已执行），
        返回 False 表示任务 ID 无效（例如从未分配过）。
        """
        with self._condition:
            # 简单的 ID 范围检查，防止无效 ID 污染集合
            if task_id < 0 or task_id >= self._task_counter:
                return False
            self._cancelled_ids.add(task_id)
            return True

    def run(self):
        """启动定时器主循环（通常在单独线程中调用）"""
        self._running = True
        with self._condition:
            while self._running:
                # 堆为空：等待新任务加入
                if not self._task_queue:
                    self._condition.wait()   # 阻塞直到被 add_task 唤醒
                    continue

                execute_time, _, task_id, callback, args, kwargs = self._task_queue[0]
                now = time.time()

                if now >= execute_time:
                    heapq.heappop(self._task_queue)
                    if task_id in self._cancelled_ids:
                        self._cancelled_ids.discard(task_id)
                        continue
                    self.ready_queue.put((callback, args, kwargs))
                    self.next_tick = 0
                else:
                    self.next_tick = execute_time - now
                    self._condition.wait(timeout=self.next_tick)

    def get_info(self):
        return self._task_queue.copy()
    
    def stop(self):
        """停止定时器循环"""
        with self._condition:
            self._running = False
            self._condition.notify()

            
# 全局定时器实例
_timer_instance: Optional[MinHeapTimer] = None
_timer_thread: Optional[threading.Thread] = None

def get_timer() -> MinHeapTimer:
    """获取全局定时器实例"""
    global _timer_instance
    if _timer_instance is None:
        _timer_instance = MinHeapTimer()
    return _timer_instance

def start_timer_thread():
    """启动定时器线程"""
    global _timer_thread, _timer_instance
    if _timer_thread is None or not _timer_thread.is_alive():
        timer = get_timer()
        _timer_thread = threading.Thread(target=timer.run, daemon=True)
        _timer_thread.start()
        return True
    return False