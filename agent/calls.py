from typing import Dict, List, Any, Optional
import openai
from memory.memory import Message



class OpenAIClient:

    def __init__(self, api_key: str, base_url : str, model: str = "qwen-plus"):
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.temperature = 0.7
        self.max_tokens = None
        
    def create_chat_completion(
        self,
        messages: List[Message],
        tools: Optional[List[Dict]] = None,
        thinking: bool = False, 
        thinking_effor: str = "High"
    ) -> Dict[str, Any]:

        # 转换消息格式
        openai_messages = []
        for msg in messages:
            '''
            message_dict = {"role": msg.role, "content": msg.content}
            if msg.name:
                message_dict["name"] = msg.name
            if msg.tool_calls:
                message_dict["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                message_dict["tool_call_id"] = msg.tool_call_id
            '''
            openai_messages.append(msg.to_dict())
        print("thinking~")
        if thinking:
            # 调用 OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                tools=tools,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                reasoning_effort=thinking_effor,
                extra_body={"thinking": {"type": "enabled"}}
            )
        else:
            # 调用 OpenAI API
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                tools=tools,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                extra_body={"thinking": {"type": "disabled"}}
            )

        print("thinking ok~")
        return response.model_dump()

