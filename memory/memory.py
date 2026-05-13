from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, fields, asdict
from datetime import datetime, date
import json
import os
from abc import ABC, abstractmethod


@dataclass
class Message:
    """对话消息结构"""
    role: Optional[str] = None  # "system", "user", "assistant", "tool"
    content: Optional[str] = None
    name: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None
    reasoning_content: Optional[str] = None
    refusal: Optional[str] = None
    annotations: Optional[str] = None
    audio: Optional[str] = None
    function_call: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Message':
        return cls(**data)


class Context:
    def __init__(self, system_prompt: Optional[str] = None, context_id: Optional[str] = None):
        """
        初始化上下文
        
        :param system_prompt: 系统提示词
        :param context_id: 上下文ID,用于标识不同的上下文会话
        """

        self.message_list: List[Message] = []
        self.context_id = context_id or self._generate_context_id()
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.read_pos = 0
        self.current_prompt_len = 0
        # self.current_token_used = 0

        if system_prompt:
            self.system_prompt = Message(role="system", content=system_prompt)
        else:
            self.system_prompt = Message(role="system", content="")

        self.message_list.append(self.system_prompt)

    def _generate_context_id(self) -> str:
        return f"context_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    
    def get_current_len(self):
        return len(self.message_list) - self.read_pos

    def map_type_to_size(self, type:str):
        if type == 'str':
            return self.current_prompt_len
        else:
            return self.get_current_len()
        

    def append(self, message: Message):
        self.message_list.append(message)
        self.current_prompt_len += len(message.content)
        self.updated_at = datetime.now()
    
    def extend(self, messages: List[Message]):
        self.message_list.extend(messages)
        self.updated_at = datetime.now()
    
    def clear(self):
        self.message_list = []
        self.message_list.append(self.system_prompt)
        self.updated_at = datetime.now()
        self.current_prompt_len = 0

    def reset(self):
        self.clear()
        self.created_at = datetime.now()

    
    def trace_back(self, steps: int = 1) -> bool:
        """
        回溯指定步数的消息
        
        :param steps: 回溯步数,1表示上一条消息
        """
        if steps <= 0 or steps > len(self.message_list)-1:
            return False
        
        self.message_list = self.message_list[:len(self.message_list)-steps]
        return True

    
    @property
    def messages(self) -> List[Message]:
        return self.message_list[self.read_pos:]
    
    
    @property
    def count(self) -> int:
        return len(self.message_list)
    
    def to_dict(self) -> Dict:
        return {
            "context_id": self.context_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "message_count": self.count,
            "read_pos": self.read_pos,
            "system_message": self.system_prompt.to_dict(),
            "messages": [msg.to_dict() for msg in self.message_list]
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Context':
        context = cls(context_id=data.get("context_id"))
        context.created_at = datetime.fromisoformat(data["created_at"])
        context.updated_at = datetime.fromisoformat(data["updated_at"])
        context.read_pos = data.get("read_pos", 0)
        context.system_prompt = Message.from_dict(data["system_message"])
        context.message_list = [Message.from_dict(msg) for msg in data["messages"]]
        return context
    
    
    def __repr__(self) -> str:
        return f"Context(id={self.context_id}, messages={self.count}, created={self.created_at})"


class Base_Memory(ABC):
    def __init__(self, path: Optional[str] = None, max_context_size: int = 1000):
        self.path = path
        self.contexts: Dict[str, Context] = {}
        self.max_context_size = max_context_size
    
    def append(self, context_id:str, message: Message) -> bool:
        if context_id in self.contexts.keys():
            self.contexts.get(context_id).append(message)
            return True
        return False


    @abstractmethod
    def save(self, context_id: str) -> bool:
        """
        保存上下文到记忆
        
        :param context: 要保存的上下文
            
        Returns: 保存是否成功
        """
        pass
    
    @abstractmethod
    def load(self, context_id: str):
        """
        从记忆加载上下文
        
        :param context_id: 上下文ID
            
        """
        pass
    
    @abstractmethod
    def trace_back(self, context_id: str, steps: int = 1):
        """
        回溯指定上下文的记忆
        
        :param context_id: 上下文ID
        :param steps: 回溯步数
            
        Returns: 回溯到的消息,如果步数超出范围则返回None
        """
        pass
    
    def create_context(self, system_prompt: Optional[str] = None, context_id: Optional[str] = None) -> str:
        if context_id in self.contexts:
            self.reset_context(context_id)

        context = Context(system_prompt=system_prompt, context_id=context_id)
        self.contexts[context.context_id] = context
        return context.context_id
    
    def get_context(self, context_id: str) -> Optional[Context]:
        return self.contexts.get(context_id)
    
    '''
    def get_context_agent_message(self, context_id: str) -> List[Message]:
        """
        获取指定ID的提供给agent上下文
        
        :param context_id: 上下文ID
            
        Returns:
            上下文实例,如果不存在则返回None
        """
        if self._limit_policy is not None:
            return self._limit_policy(self.contexts.get(context_id))
        
        return self.contexts.get(context_id).messages
    '''


    def list_contexts(self) -> List[str]:
        return list(self.contexts.keys())
    
    def reset_context(self, context_id: str) -> bool:
        if context_id in self.contexts:
            self.save(context_id)
            self.contexts[context_id].reset()
            return True
        
        return False

    def delete_context(self, context_id: str) -> bool:
        if context_id in self.contexts:
            del self.contexts[context_id]
            return True
        return False


class Memory(Base_Memory):
    def __init__(self, path: Optional[str] = None, 
                 load_path: Optional[str] = None, 
                 system_prompt: Optional[str] = None, 
                 context_name: Optional[str] = None,
                 max_context_size: int = 1000):
        """
        初始化内存记忆系统

        :param path: 记忆存储路径,默认为'history'文件夹
        :param load_path: 加载内存上下文路径,默认为无
        :param system_prompt: 默认系统prompt,默认为无
        :param context_name: 上下文名字,默认为无
        """

        if path is None:
            path = os.path.join("history", str(date.today()))
        super().__init__(path, max_context_size)
        
        os.makedirs(self.path, exist_ok=True)
        
        if load_path is not None:
            self.load(load_path)
        elif context_name is not None:
            self.create_context(system_prompt, context_name)
   
    
    def _generate_filename(self, context_id: str) -> str:
        day = str(date.today())
        os.makedirs(os.path.join(self.path, context_id, day), exist_ok=True)
        
        # timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        timestamp = self.contexts[context_id].created_at.strftime('%Y%m%d_%H%M%S')
        
        return os.path.join(context_id, day, f"{timestamp}.json")
    
    def save(self, context_id: str) -> bool:
        """
        保存上下文到JSON文件
        
        :param context: 要保存的上下文id
            
        Returns:
            保存是否成功
        """
        try:
            # 生成文件名
            filename = self._generate_filename(context_id)

            filepath = os.path.join(self.path, filename)


            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.contexts[context_id].to_dict(), f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"保存上下文 {self.contexts[context_id]} 时出错: {e}")
            return False
    
    def load(self, load_path: Optional[str] = None):
        if load_path is None:
            pass

        if not os.path.isfile(load_path) and not load_path.endswith('.json'):
            pass
        

        try:
            with open(load_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            context = Context.from_dict(data)
            self.contexts[context.context_id] = context
        except Exception as e:
            print(f"加载记忆文件 {load_path} 时出错: {e}")
    
    def trace_back(self, context_id: str, steps: int = 1) -> bool:
        """
        回溯指定上下文的记忆
        
        :param ontext_id: 上下文ID
        :param steps: 回溯步数
            
        Returns:
            回溯到的消息,如果步数超出范围则返回None
        """
        context = self.get_context(context_id)

        
        if context is None:
            return False
        
        return context.trace_back(steps)
    
    def reset(self):
        self.save_all()
        self.contexts = {}

    def save_all(self) -> bool:
        success = True
        for context in self.contexts.keys():
            if not self.save(context):
                success = False
        
        return success
    
