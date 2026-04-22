from agent.calls import OpenAIClient
from typing import Dict, List, Optional
from memory.memory import Context, Message, Memory

from tool.tools import get_tool_registry
import json
from btf_print import LogPrinter


printer = LogPrinter()


def print_message(Message, response, splt = '-'):
  
    printer.print(splt*50)
    printer.print(Message)
    printer.print("---------------------- response is ----------------------")
    printer.print(response)
    printer.print(splt*50)


import inspect
class agent:
    def __init__(self, api_key: str, base_url : str, model: str = "qwen-plus",
                 load_path: Optional[str] = None, system_prompt: Optional[str] = None, context_name: Optional[str] = None):
        self.client = OpenAIClient(api_key, base_url, model)
        self.tools_manager = get_tool_registry()

        self.system_prompt = system_prompt

        self.memory = Memory("history", load_path, system_prompt, context_name)
    

        
        self.max_epoch = 20

    async def close(self):
        if not self.memory.save_all():
            print("save failed")
        await self.tools_manager.cleanup_all()

    
    
    async def response(self, usr_msg: str, context_id: str):

        now_context = self.memory.get_context(context_id)
        if now_context is None:
            return "错误id"
        
        now_context.append(Message(role="user", content=usr_msg))

        step = 0
        while step < self.max_epoch:
            # 获取模型响应
            response = self.client.create_chat_completion(
                now_context.messages, # self.context.message 返回完整列表
                tools=self.tools_manager.get_tool_definitions()
            )
            
            response_message = response["choices"][0]["message"]
            # 将模型的消息存入上下文
            now_context.append(Message(
                role="assistant",
                content=response_message.get("content") or "",
                tool_calls=response_message.get("tool_calls")
            ))

            # 如果没有工具调用，直接跳出循环
            if not response_message.get("tool_calls"):
                print_message(now_context.messages, response, 'p') 
                break

            # 执行工具调用
            tool_results = await self._execute_tool_calls(response_message["tool_calls"])
            
            # 逐个添加工具执行结果
            for tool_call,  result in tool_results:
                # MCP 格式处理逻辑
                from mcp import types
                format_result = result
                if isinstance(result, list) and len(result) > 0 and isinstance(result[0], types.TextContent):
                    format_result = result[0].model_dump()
                
                now_context.append(Message(
                    role="tool",
                    content=json.dumps(format_result),
                    tool_call_id=tool_call["id"]
                ))
            
            step += 1
            print_message(now_context.messages, response, 't') # 打印当前轨迹

        # 超过最大轮数强制总结
        if step >= self.max_epoch and response_message.get("tool_calls"):
            now_context.append(Message(role="system", content="已达到工具调用上限，请根据现有信息直接回答。"))
            final_response = self.client.create_chat_completion(now_context.messages)
            response_message = final_response["choices"][0]["message"]
            now_context.append(Message(role="assistant", content=response_message["content"]))
        
        return response_message.get("content", "")


    async def _execute_tool_calls(self, tool_calls: List[Dict]) -> List[tuple]:
        """执行工具调用"""
        results = []
        
        for tool_call in tool_calls:
            tool_name = tool_call["function"]["name"]
            arguments = json.loads(tool_call["function"]["arguments"])
            
            tool = self.tools_manager.get_tool(tool_name)
            if tool:
                if inspect.iscoroutinefunction(tool.func):
                    result = await tool.func(**arguments)
                else:
                    result = tool.func(**arguments)

                results.append((tool_call, result))
            else:
                results.append(f"tool {tool_name} not exist")
            
        return results