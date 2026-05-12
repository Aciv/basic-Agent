from agent.calls import OpenAIClient
from typing import Dict, List, Optional
from memory.memory import Message, Memory
from IO.channel_base import TransportMessage
import asyncio
from tool.tools import get_tool_registry
import json
from btf_print import LogPrinter


printer = LogPrinter()


def print_message(Message, response, splt = '-'):
    # return
    printer.print(splt*50)
    printer.print(Message)
    printer.print("---------------------- response is ----------------------")
    printer.print(response)
    printer.print(splt*50)


import inspect
class Agent:
    def __init__(self, api_key: str, base_url : str, model: str = "qwen-plus",
                limit_policy: Optional[callable] = None, 
                load_path: Optional[str] = None, 
                system_prompt: Optional[str] = None, 
                context_name: Optional[str] = None,
                thought_output: Optional[asyncio.Queue] = None,
                thought_max_epoch: Optional[int] = 30,
                context_max_size: int = 1000):
        
        self.client = OpenAIClient(api_key, base_url, model)
        self.tools_manager = get_tool_registry()

        self.limit_policy = limit_policy

        self.system_prompt = system_prompt
        
        self.memory = Memory(path="history", load_path=load_path, 
                             max_context_size = context_max_size,
                            system_prompt=system_prompt, context_name=context_name)
        self.thought_output = thought_output

        self.max_epoch = thought_max_epoch

    async def close(self):
        if not self.memory.save_all():
            print("save failed")
        await self.tools_manager.cleanup_all()

    
    
    async def response(self, usr_msg: str, context_id: str, thinking: bool = False, thinking_effor: str = "High"):

        if context_id not in self.memory.list_contexts():
            return "wrong id"
        
        context = self.memory.get_context(context_id)
        if context.count >= self.memory.max_context_size:
            # print("touch the max fuck you oh!!!!!!!!")
            self.memory.save(context_id)
            context.reset()


        if self.limit_policy is not None:
            self.limit_policy(context)


        self.memory.append(context_id, Message(role="user", content=usr_msg))

        step = 0
        while step < self.max_epoch:

            response = self.client.create_chat_completion(
                messages=context.messages, 
                tools=self.tools_manager.get_tool_definitions(),
                thinking=thinking,
                thinking_effor=thinking_effor
            )
            
            response_message = response["choices"][0]["message"]
            await self._handle_message(response_message, context_id)
            
            '''
            msg = self.get_Message(response_message)

            now_context.append(Message(**msg))

            if self.thought_output is not None and msg['content'] != "":
                await self.thought_output.put(TransportMessage(
                context_id=context_id,
                output_id="",
                content=msg.get('content')
            ))
            '''

            '''
            now_context.append(Message(
                role=response_message.get("role") or "assistant",
                content=response_message.get("content") or "",
                tool_calls=response_message.get("tool_calls"),
                reasoning_content=response_message.get("reasoning_content"),
            ))
            '''

            if not response_message.get("tool_calls"):
                # print_message(now_context.messages, response, 'p') 
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
                
                self.memory.append(context_id, Message(
                    role="tool",
                    content=json.dumps(format_result),
                    tool_call_id=tool_call["id"]
                ))
            
            step += 1
            print_message(context.messages, response, 't') # 打印当前轨迹

        # 超过最大轮数强制总结
        if step >= self.max_epoch and response_message.get("tool_calls"):
            print("the max arrived")
            self.memory.append(context_id, Message(
                role="system", 
                content="已达到工具调用上限，请根据现有信息直接回答。"))
            
            final_response = self.client.create_chat_completion(
                messages=context.messages,                 
                thinking=thinking,
                thinking_effor=thinking_effor)
            response_message = final_response["choices"][0]["message"]

            await self._handle_message(response_message, context_id, False)



        return response_message.get("content", "")

    async def _handle_message(self, raw_message, context_id, thought_out = True):
        '''
        role = raw_message.get("role") or "assistant",
        content = raw_message.get("content") or ""
        tool_calls = raw_message.get("tool_calls") or None   
        '''
        reasoning = raw_message.get("reasoning_content")  

        msg_kwargs = {
            "role": raw_message.get("role") or "assistant",
            "content": raw_message.get("content") or "",
            "tool_calls": raw_message.get("tool_calls"), 
            "annotations": raw_message.get("annotations"), 
            "audio": raw_message.get("audio"),
            "function_call": raw_message.get("function_call"),            
        }


        if reasoning is not None:
            msg_kwargs["reasoning_content"] = reasoning

        self.memory.append(context_id, Message(**msg_kwargs))

        if self.thought_output is not None and msg_kwargs['content'] != "" and raw_message.get("tool_calls") is not None and thought_out:
            await self.thought_output.put(TransportMessage(
            context_id=context_id,
            output_id="",
            content=msg_kwargs.get('content')
        ))


    
    
    async def _execute_tool_calls(self, tool_calls: List[Dict]) -> List[tuple]:
        """执行工具调用"""
        results = []
        
        for tool_call in tool_calls:
            tool_name = tool_call["function"]["name"]
            arguments = json.loads(tool_call["function"]["arguments"])
            
            printer.print(f"tool {tool_name} is calliing")
            printer.print(arguments)
            
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