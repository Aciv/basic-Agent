import asyncio
import queue
import sys
import logging
from typing import Dict, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',            
    handlers=[
        logging.FileHandler('log/output.log', 'w', encoding='utf-8'),  
        # logging.StreamHandler()                        
    ]
)

from agent.agent import Agent
from mcp_loader.mcp_register import get_mcp_server
from timer_schedule import get_timer

import addition_tool
from memory.system_prompt import make_system_prompt
from middle.limit_policy import truncate_policy, summarize_policy, simple_response



from IO.channel_base import TransportMessage
from IO.std_channel import StdInChannel, StdOutChannel

if __name__ == "__main__":

    
    async def agent_worker(agent: Agent, input_queue: asyncio.Queue, output_dict: Dict[str, asyncio.Queue], worker_id: int):
        while True:  
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
            
            response = await agent.response(usr_msg=data.content, context_id=data.context_id)

            await output_dict[data.output_id].put(TransportMessage(
                context_id=data.context_id,
                output_id=data.output_id,
                content=response
            ))
            input_queue.task_done()

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


        sem = asyncio.Semaphore(0) 
        # 创建队列
        input_queue = asyncio.Queue()
        output_dict = {}

        # 创建输入/输出通道
        stdin_ch = StdInChannel(input_queue, prompt="You: ", semaphore=sem)
        std_output_queue = asyncio.Queue()
        stdout_ch = StdOutChannel(output_queue=std_output_queue, semaphore=sem)
        output_dict[stdout_ch.name] = std_output_queue

        # 启动通道
        stdin_ch.start()
        stdout_ch.start()

        # 初始化agent
        system_prompt = make_system_prompt(system_context_path, skills_dir)
        agent = Agent(key, base_url, model, 
                    limit_policy=summarize_policy(summarize_agent=simple_response, summarized_limit=100),
                    context_max_size=1000,
                    system_prompt=system_prompt, context_name=stdin_ch.get_name(),
                    thought_output=std_output_queue)
        
        # 加载MCP服务器
        await get_mcp_server(mcp_path)

        timer = get_timer(input_queue)
        timer_workers = asyncio.create_task(timer.run())
        workers = [asyncio.create_task(agent_worker(agent, input_queue, output_dict, i)) for i in range(1)]
        workers.append(timer_workers)
        try:
            await asyncio.gather(*workers)
        except  (asyncio.CancelledError,EOFError, KeyboardInterrupt):
            print("\n检测到退出信号，正在清理资源...")
        finally:
            await stdin_ch.stop()
            input_queue.task_done()
            await input_queue.join()

            await stdout_ch.stop()
            for o_queue in output_dict.values():
                await o_queue.join()

            for w in workers:
                if not w.done():
                    w.cancel()

            await asyncio.gather(*workers, return_exceptions=True)
            await agent.close()
            logging.shutdown()
            print("程序已正常退出")
    try:
        asyncio.run(main("config.json"))
    except KeyboardInterrupt:
        print("\n用户中断，正在停止...")