from memory.memory import Context, Message
from typing import Callable, List
from agent.calls import OpenAIClient

class truncate_policy:
    def __init__(self, truncated_type = 'Message', truncated_limit = 100):
        self.truncated_type = truncated_type
        self.truncated_limit = truncated_limit

    def __call__(self, client: OpenAIClient, context : Context):
        if context.map_type_to_size(self.truncated_type) < self.truncated_limit:
            return
        

        context.read_pos = context.count
        context.append(context.system_prompt)


def simple_response(client: OpenAIClient, messages: List[Message]) -> str:

    response = client.create_chat_completion(
            messages=messages, 
            tools=[],
        )
        
    response_message = response["choices"][0]["message"]
    return response_message.get("content", "")

class summarize_policy:
    def __init__(self, summarize_agent: Callable[[OpenAIClient, List[Message]], str],
                summarized_type = 'Message',summarized_limit = 100):
        self.truncated_type = summarized_type
        self.truncated_limit = summarized_limit
        self.summarize_agent = summarize_agent


    def __call__(self, client: OpenAIClient, context : Context):
        if context.map_type_to_size(self.truncated_type) < self.truncated_limit:
            return

        summarize_prompt = Message(role='user',
                                   content="已到达上下文限制,你需要根据现在的聊天内容," \
                                           "生成一个聊天内容的总结,需要记住关键信息")
        
        context.append(summarize_prompt)


        summarized_message = self.summarize_agent(client, context.messages)
        

        new_system_message = Message(role='system', 
                                    content=context.system_prompt.content + summarized_message)
    
        context.read_pos = context.count
        context.append(new_system_message)

