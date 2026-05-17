import asyncio
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.FileHandler('log/output.log', 'w', encoding='utf-8')]
)

from agent.agent import Agent
from mcp_loader.mcp_register import get_mcp_server
from memory.system_prompt import make_system_prompt
from middle.limit_policy import summarize_policy, simple_response

from IO.channel_base import TransportMessage
from IO.websocket_channel import WsServer, WsInChannel, WsOutChannel


async def agent_worker(agent, in_queue, out_queue):
    while True:
        try:
            data = await asyncio.wait_for(in_queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            continue
        if data.content is None:
            in_queue.task_done()
            continue
        response = await agent.response(usr_msg=data.content, context_id=data.context_id)
        await out_queue.put(TransportMessage(
            context_id=data.context_id, output_id=data.output_id,
            content=response
        ))
        in_queue.task_done()


async def main(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)["agent_system_config"]

    in_queue, out_queue = asyncio.Queue(), asyncio.Queue()
    
    system_prompt = make_system_prompt(config["system_context_path"], config["skills_dir"])
    agent = Agent(config["key"], config["base_url"], config["model"],
                  limit_policy=summarize_policy(summarize_agent=simple_response, summarized_limit=100),
                  context_max_size=1000, system_prompt=system_prompt,
                  thought_output=out_queue)
    await get_mcp_server(config["mcp_path"])

    server = WsServer(host="0.0.0.0", port=8082)
    server.add_static("/", "./frontend/index.html")
    WsInChannel(in_queue, server)
    out_ch = WsOutChannel(out_queue, server)

    await server.start()
    out_ch.start()
    worker = asyncio.create_task(agent_worker(agent, in_queue, out_queue))

    try:
        await asyncio.Event().wait()
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        worker.cancel()
        await out_ch.stop()
        await server.stop()
        await agent.close()


if __name__ == "__main__":
    try:
        asyncio.run(main("config.json"))
    except KeyboardInterrupt:
        print("\n用户中断")
