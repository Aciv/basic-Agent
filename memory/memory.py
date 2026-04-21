from typing import Dict, List, Any, Optional
from dataclasses import dataclass, fields

@dataclass
class Message:
    """对话消息结构"""
    role: str  # "system", "user", "assistant", "tool"
    content: Optional[str] = None
    name: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None


class Context:
    def __init__(self, system_prompt):
        self.message_list = []
        self.message_list.append(system_prompt)

    def append(self, message: Message):
        self.message_list.append(message)

    @property
    def message(self):
        return self.message_list
    
    