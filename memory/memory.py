from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, fields, asdict
from datetime import datetime, date
import json
import os
from abc import ABC, abstractmethod


@dataclass
class Message:
    """对话消息结构"""
    role: str  # "system", "user", "assistant", "tool"
    content: Optional[str] = None
    name: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Message':
        """从字典创建Message实例"""
        return cls(**data)


class Context:
    """上下文载体类，支持回溯和永久保存"""
    
    def __init__(self, system_prompt: Optional[str] = None, context_id: Optional[str] = None):
        """
        初始化上下文
        
        :param system_prompt: 系统提示词
        :param context_id: 上下文ID，用于标识不同的上下文会话
        """
        self.message_list: List[Message] = []
        self.context_id = context_id or self._generate_context_id()
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        
        if system_prompt:
            self.append(Message(role="system", content=system_prompt))
    
    def _generate_context_id(self) -> str:
        """生成上下文ID"""
        return f"context_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    
    def append(self, message: Message):
        """添加消息到上下文"""
        self.message_list.append(message)
        self.updated_at = datetime.now()
    
    def extend(self, messages: List[Message]):
        """批量添加消息"""
        self.message_list.extend(messages)
        self.updated_at = datetime.now()
    
    def clear(self):
        """清空上下文（保留系统提示）"""
        if self.message_list and self.message_list[0].role == "system":
            system_message = self.message_list[0]
            self.message_list = [system_message]
        else:
            self.message_list = []
        self.updated_at = datetime.now()
    
    
    def trace_back(self, steps: int = 1) -> bool:
        """
        回溯指定步数的消息
        
        :param steps: 回溯步数，1表示上一条消息
        """
        if steps <= 0 or steps > len(self.message_list)-1:
            return False
        
        self.message_list = self.message_list[:len(self.message_list)-steps]
        return True

    
    @property
    def messages(self) -> List[Message]:
        """获取所有消息"""
        return self.message_list
    
    @property
    def count(self) -> int:
        """获取消息数量"""
        return len(self.message_list)
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "context_id": self.context_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "message_count": self.count,
            "messages": [msg.to_dict() for msg in self.message_list]
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Context':
        """从字典创建Context实例"""
        context = cls(context_id=data.get("context_id"))
        context.created_at = datetime.fromisoformat(data["created_at"])
        context.updated_at = datetime.fromisoformat(data["updated_at"])
        context.message_list = [Message.from_dict(msg) for msg in data["messages"]]
        return context
    
    
    def __repr__(self) -> str:
        """"print调用"""
        return f"Context(id={self.context_id}, messages={self.count}, created={self.created_at})"


class Base_Memory(ABC):
    """记忆基类，定义记忆系统的通用接口"""
    
    def __init__(self, path: Optional[str] = None):
        """
        初始化记忆系统
        
        :param path: 记忆存储路径
        """
        self.path = path
        self.contexts: Dict[str, Context] = {}
    
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
            
        Returns: 回溯到的消息，如果步数超出范围则返回None
        """
        pass
    
    def create_context(self, system_prompt: Optional[str] = None, context_id: Optional[str] = None) -> str:
        """
        创建新的上下文
        
        :param system_prompt: 系统提示词
            
        Returns: 新创建的上下文
        """
        context = Context(system_prompt=system_prompt, context_id=context_id)
        self.contexts[context.context_id] = context
        return context.context_id
    
    def get_context(self, context_id: str) -> Optional[Context]:
        """
        获取指定ID的上下文
        
        :param context_id: 上下文ID
            
        Returns:
            上下文实例，如果不存在则返回None
        """
        return self.contexts.get(context_id)
    
    def list_contexts(self) -> List[str]:
        """
        列出所有上下文ID
        
        Returns:
            上下文ID列表
        """
        return list(self.contexts.keys())
    
    def delete_context(self, context_id: str) -> bool:
        """
        删除指定上下文
        
        :param context_id: 上下文ID
            
        Returns:
            删除是否成功
        """
        if context_id in self.contexts:
            del self.contexts[context_id]
            return True
        return False


class Memory(Base_Memory):
    """具体记忆实现类，将记忆保存在history/文件夹下以时间为文件名的json文件中"""
    
    def __init__(self, path: Optional[str] = None, load_path: Optional[str] = None, system_prompt: Optional[str] = None, context_name: Optional[str] = None):
        """
        初始化内存记忆系统
        
        :param path: 记忆存储路径，默认为'history'文件夹
        :param load_path: 加载内存上下文路径，默认为无
        :param system_prompt: 默认系统prompt，默认为无
        :param context_name: 上下文名字，默认为无
        
        """
        if path is None:
            path = os.path.join("history", str(date.today()))
        super().__init__(path)
        
        # 确保存储目录存在
        os.makedirs(self.path, exist_ok=True)
        
        # 加载已存在的记忆
        if load_path is not None:
            self.load(load_path)
        else:
            self.create_context(system_prompt, context_name)
   
    
    def _generate_filename(self, context_id: str) -> str:
        """根据上下文ID和时间生成文件名"""

        day = str(date.today())
        os.makedirs(os.path.join(self.path,day), exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return os.path.join(day, f"{timestamp}_{context_id}.json")
    
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
            
            # 保存到JSON文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.contexts[context_id].to_dict(), f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"保存上下文 {self.contexts[context_id]} 时出错: {e}")
            return False
    
    def load(self, load_path: Optional[str] = None):
        """加载已存在的记忆文件"""
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
            回溯到的消息，如果步数超出范围则返回None
        """
        context = self.get_context(context_id)

        
        if context is None:
            return False
        
        return context.trace_back(steps)
    def reset(self):
        """重置Memory"""
        self.contexts = {}

    def save_all(self) -> bool:
        """
        保存所有上下文到文件
        
        Returns:
            保存是否成功
        """
        success = True
        for context in self.contexts.keys():
            if not self.save(context):
                success = False
        
        return success
    
