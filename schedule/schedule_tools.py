"""
定时任务工具模块
提供定时任务相关的工具,允许agent添加定时任务并指定回调函数
"""

import time
import json
from typing import Dict, Any, Callable, Optional, Union
from pathlib import Path
from enum import Enum

from tool.tools import tool
from schedule.timer import get_timer, start_timer_thread


class Task_type(str, Enum):  # 继承 str 很重要,便于 JSON 交互
    SUB_AGENT = "sub_agent"
    MAIN_AGENT = "main_agent"


@tool
def schedule_task(
    delay_seconds: float,
    task_name: str,
    prompt: str, 
    task_type: Task_type = Task_type.SUB_AGENT,
    callback_function: Optional[str] = None
) -> Dict[str, Any]:
    """
    添加定时任务工具,在指定的延迟后执行任务
    
    :param delay_seconds: 延迟时间（秒）
    :param task_name: 任务名称
    :param prompt: 输入给agent的user prompt
    :param task_type: 任务类型,目前支持 "sub_agent"（使用全新上下文调用）或 "main_agent"（在当前上下文调用）
    :param callback_function: 回调函数,默认为无
    :return: 操作结果信息
    """
    try:
        # 确保定时器线程已启动
        start_timer_thread()
        
        timer = get_timer()
        
        # 准备任务数据

        
        # 创建任务记录
        task_record = {
            "name": task_name,
            "type": task_type,
            "user_prompt": prompt,
            "scheduled_time": time.time() + delay_seconds,
            "callback_function": callback_function
        }

        '''
        # 保存任务记录到文件（可选）
        task_file = Path("scheduled_tasks.json")
        tasks = []
        if task_file.exists():
            try:
                with open(task_file, 'r', encoding='utf-8') as f:
                    tasks = json.load(f)
            except:
                tasks = []
        
        tasks.append(task_record)
        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2)
        '''



        def function_callback():
            return {
                        "task_name": task_name,
                        "task_type": task_type,
                        "user_prompt": prompt,
                        "callback_function": callback_function
                    }
        
        timer.add_task(delay_seconds, task_name, function_callback)


        
        return {
            "success": True,
            "message": f"定时任务已添加: {task_name}",
            "task_name": task_name,
            "delay_seconds": str(delay_seconds),
            "scheduled_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(task_record['scheduled_time'])),
            "task_type": task_type,
            "user_prompt": prompt
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"添加定时任务失败: {str(e)}",
            "error": str(e)
        }

@tool
def list_scheduled_tasks() -> Dict[str, Any]:
    """
    列出当前的定时任务，返回data为任务元组(执行时间, 任务名, 任务id, 回调函数, args, kwargs)组成的列表
    
    :return: 定时任务列表信息
    """
    # 确保定时器线程已启动
    start_timer_thread()
    
    timer = get_timer()
    lines = [" ".join(str(x) for x in tup) for tup in timer.get_info()]

    return {
            "success": True,
            "data": "\n".join(lines)
    }


@tool
def cancel_scheduled_task(task_id: int) -> Dict[str, Any]:
    """
    取消指定的定时任务
    
    :param task_id: 要取消的任务的id,由list_scheduled_tasks获得
    :return: 操作结果信息
    """
    # 确保定时器线程已启动
    start_timer_thread()
    
    timer = get_timer()

    return {
            "success": timer.cancel_task(task_id)
    }

        




__all__ = [
    'schedule_task',
    'list_scheduled_tasks',
    'cancel_scheduled_task',
]