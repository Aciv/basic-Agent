from agent.calls import OpenAIClient
from typing import Dict, List, Any, Optional
from memory.memory import Context, Message




from tool.tools import get_tool_registry, tool

from typing import Literal, Optional 
import json


from btf_print import LogPrinter,logging


printer = LogPrinter()


def print_message(Message, response, splt = '-'):
    logging.info("直接测试")
    printer.print(splt*50)
    printer.print(Message[-1])
    printer.print("---------------------- response is ----------------------")
    printer.print(response)
    printer.print(splt*50)


import inspect
class agent:
    def __init__(self, system_prompt : Message, api_key: str, base_url : str, model: str = "qwen-plus", ):
        self.client = OpenAIClient(api_key, base_url, model)
        self.tools_manager = get_tool_registry()
        self.context = Context(system_prompt)
        self.system_prompt = system_prompt

    async def close(self):
        await self.tools_manager.cleanup_all()

    async def response_with_empty_context(self, usr_msg):

        tmp_context = Context(self.system_prompt)

        tmp_context.append(Message(role="user", content=usr_msg))



        response = self.client.create_chat_completion(tmp_context.message,
                        tools=self.tools_manager.get_tool_definitions())

        response_message = response["choices"][0]["message"]

        print_message(tmp_context.message, response, 'p')

        while response_message.get("tool_calls"):
            # 执行工具调用
            tool_results = await self._execute_tool_calls(
                response_message["tool_calls"]
            )
            
            # 添加工具响应
            for tool_call, result in tool_results:
                tmp_context.append(
                    Message(
                        role="assistant",
                        tool_calls=[
                            {
                                'type': 'function', 
                                'id': f'{tool_call["id"]}', 
                                'function': {'name': f'{tool_call["function"]["name"]}', 
                                            'arguments': tool_call["function"]["arguments"] }
                            }
                        ]
                    )
                )
                from mcp import types
                format_result = {}
                if isinstance(result, list) and isinstance(result[0], types.TextContent):
                    for content_item in result:
                        if isinstance(content_item, types.TextContent):
                            format_result = content_item.model_dump()
                else:
                    format_result = result


                tmp_context.append(
                    Message(
                        role="tool",
                        content=json.dumps(format_result),
                        tool_call_id=tool_call["id"]
                    )
                )


            response = self.client.create_chat_completion(tmp_context.message,
                tools=self.tools_manager.get_tool_definitions())


            print_message(tmp_context.message, response, 't')

            tmp_context.append(Message(role="assistant", content=response_message["content"]))
            response_message = response["choices"][0]["message"]
        
        return response_message["content"]
    
    async def response(self, usr_msg):

        self.context.append(Message(role="user", content=usr_msg))



        response = self.client.create_chat_completion(self.context.message,
                        tools=self.tools_manager.get_tool_definitions())

        response_message = response["choices"][0]["message"]

        print_message(self.context.message, response, 'p')

        while response_message.get("tool_calls"):
            # 执行工具调用
            tool_results = await self._execute_tool_calls(
                response_message["tool_calls"]
            )
            
            # 添加工具响应
            for tool_call, result in tool_results:
                self.context.append(
                    Message(
                        role="assistant",
                        tool_calls=[
                            {
                                'type': 'function', 
                                'id': f'{tool_call["id"]}', 
                                'function': {'name': f'{tool_call["function"]["name"]}', 
                                             'arguments': tool_call["function"]["arguments"] }
                            }
                        ]
                    )
                )
                from mcp import types
                format_result = {}
                if isinstance(result, list) and isinstance(result[0], types.TextContent):
                    for content_item in result:
                        if isinstance(content_item, types.TextContent):
                            format_result = content_item.model_dump()
                else:
                    format_result = result


                self.context.append(
                    Message(
                        role="tool",
                        content=json.dumps(format_result),
                        tool_call_id=tool_call["id"]
                    )
                )


            response = self.client.create_chat_completion(self.context.message,
                tools=self.tools_manager.get_tool_definitions())


            print_message(self.context.message, response, 't')

            self.context.append(Message(role="assistant", content=response_message["content"]))
            response_message = response["choices"][0]["message"]
        
        return response_message["content"]


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






