"""
定时任务工具模块
提供定时任务相关的工具,允许agent添加定时任务并指定回调函数
"""

import time

from typing import Dict, Any

from tool.tools import tool

from timer_schedule.timer import get_timer
from IO.channel_base import TransportMessage



@tool
async def schedule_task(
    delay_seconds: float,
    task_name: str,
    prompt: str, 
    context_id: str = "Stdin",
    output_id: str = "Stdout",
) -> Dict[str, Any]:
    """
    添加定时任务工具,在指定的延迟后执行任务
    
    :param delay_seconds: 延迟时间（秒）
    :param task_name: 任务名称
    :param prompt: 输入给agent的user prompt
    :param context_id : 输入的上下文id，默认为 "Stdin"
    :param output_id : 输出的channel ID
    :return: 操作结果信息
    """
    try:

        
        timer = get_timer()
        

        
        # 创建任务记录
        task_record = {
            "name": task_name,
            "user_prompt": prompt,
            "context_id": context_id,
            "output_id": output_id,
            "scheduled_time": time.time() + delay_seconds,
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


        message = TransportMessage(
            context_id=context_id,
            output_id=output_id,
            content=prompt
        )
        
        await timer.add_task(delay_seconds, task_name, message)


        
        return {
            "success": True,
            "message": f"定时任务已添加: {task_name}",
            "task_name": task_name,
            "delay_seconds": str(delay_seconds),
            "scheduled_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(task_record['scheduled_time'])),
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
    列出当前的定时任务，返回data为任务元组(执行时间, 任务名, 任务id, 执行信息)组成的列表
    
    :return: 定时任务列表信息
    """

    
    timer = get_timer()
    lines = [" ".join(str(x) for x in tup) for tup in timer.get_info()]

    return {
            "success": True,
            "data": "\n".join(lines)
    }


@tool
async def cancel_scheduled_task(task_id: int) -> Dict[str, Any]:
    """
    取消指定的定时任务
    
    :param task_id: 要取消的任务的id,由list_scheduled_tasks获得
    :return: 操作结果信息
    """

    
    timer = get_timer()

    return {
            "success": await timer.cancel_task(task_id)
    }

        




