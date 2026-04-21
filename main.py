import asyncio
import threading
import queue

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',            # 只输出消息本身，不额外添加时间戳等
    handlers=[
        logging.FileHandler('log/output.log', 'w', encoding='utf-8'),  # 输出到文件
        # logging.StreamHandler()                               # 同时输出到控制台
    ]
)

from agent.agent import agent
from mcp_loader.mcp_register import get_mcp_server
from memory.system_prompt import make_system_prompt
from schedule.timer import get_timer, start_timer_thread
from schedule.schedule_tools import Task_type



if __name__ == "__main__":


    def input_thread(q, semaphore):
        """用户输入线程"""
        while True:
            msg = input("user: ")
            q.put(msg)
            semaphore.acquire()

    async def main(config_path):
        import json
        try:
            with open(config_path, "r", encoding="utf-8") as config_file:
                config = json.load(config_file)
                skills_dir = config["agent_system_config"]["skills_dir"]
                system_context_path = config["agent_system_config"]["system_context_path"]
                key = config["agent_system_config"]["key"]
                base_url = config["agent_system_config"]["base_url"]
                model = config["agent_system_config"]["model"]
                mcp_path = config["agent_system_config"]["mcp_path"]
        except Exception as e:
            print(f"导入agent配置文件失败，{e}")
            exit(0)

        # 初始化agent
        aagent = agent(make_system_prompt(system_context_path, skills_dir), 
                    key, base_url, model)
        
        # 加载MCP服务器
        await get_mcp_server(mcp_path)

        # 启动定时器线程
        start_timer_thread()
        timer = get_timer()

        # 设置用户输入线程
        input_semaphore = threading.Semaphore(0)
        input_q = queue.Queue()
        input_thread_instance = threading.Thread(
            target=input_thread, 
            args=(input_q, input_semaphore), 
            daemon=True
        )
        input_thread_instance.start()


        while True:
            try:
                # 处理定时任务回调
                while True:
                    callback, args, kwargs = timer.ready_queue.get_nowait()
                    print("\n[定时任务] 执行回调函数")
                    try:
                        result = callback(*args, **kwargs)
                        task_name = result.get("task_name")
                        task_type = result.get("task_type")
                        prompt = result.get("user_prompt", "")
                        callback_function = result.get("callback_function")
                        if task_type == "main_agent":
                            out_put = await aagent.response(prompt)
                            print("user: ", prompt)
                            print("Ai: ")
                            print(out_put)
                            print("user: ", end="", flush=True)
                        else:
                            await aagent.response_with_empty_context(prompt)
                        
                        if callback_function is not None:
                            callback_function()

                    except Exception as e:
                        print(f"[定时任务] 执行出错: {e}")

            except queue.Empty:
                pass   
            
            try:
                usr_msg = input_q.get(timeout=0.1)
                
                if usr_msg == 'quit':
                    print("[系统] 正在退出...")
                    break

                # 处理agent响应
                print("thingking~")
                out_put = await aagent.response(usr_msg)
                print("Ai: ")
                print(out_put)
                input_semaphore.release()

            except queue.Empty:
                pass
            except Exception as e:
                print(f"[系统错误] {e}")

        await aagent.close()
        print("[系统] 程序已退出")

    asyncio.run(main("config.json"))