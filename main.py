import asyncio
import threading
import queue

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',            
    handlers=[
        logging.FileHandler('log/output.log', 'w', encoding='utf-8'),  
        # logging.StreamHandler()                               
    ]
)

from agent.agent import agent
from mcp_loader.mcp_register import get_mcp_server
from memory.system_prompt import make_system_prompt
from schedule.timer import get_timer, start_timer_thread
from schedule.schedule_tools import Task_type
import addition_tool
from memory.system_prompt import make_system_prompt

if __name__ == "__main__":


    def input_thread(q, semaphore):
        """用户输入线程"""
        try:
            while True:
                msg = input("user: ")
                q.put(msg)
                semaphore.acquire()
        except KeyboardInterrupt:
            print("\n用户输入中断，正在停止...")

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
        context_name = "test"
        system_prompt = make_system_prompt(system_context_path, skills_dir)
        aagent = agent(key, base_url, model, 
                    system_prompt=system_prompt, context_name="test")
        
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

        try:
            while True:
                try:
                    usr_msg = input_q.get(timeout=0.1)
                    
                    if usr_msg == 'quit':
                        print("[系统] 正在退出...")
                        break

                    # 处理agent响应
                    print("thingking~")
                    out_put = await aagent.response(usr_msg, context_name)
                    print("Ai: ")
                    print(out_put)
                    input_semaphore.release()

                except queue.Empty:
                    pass

                except Exception as e:
                    print(f"[系统错误] {e}")
        except asyncio.CancelledError:
                print("\n[系统] 收到退出信号，正在清理...")
        except Exception as e:
            print(f"agent执行错误 {e}")
        finally:
            print("clossing")
            await aagent.close()



        
        print("[系统] 程序已退出")
    try:
        asyncio.run(main("config.json"))
    except KeyboardInterrupt:
        print("\n用户中断，正在停止...")