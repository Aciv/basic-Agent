"""
Agent 工具装饰器模块
支持 pydantic 参数格式与 description 描述，自动提取函数名
"""

import inspect
import functools
from typing import Callable, Any, Dict, List, Optional, Type, get_type_hints
from pydantic import BaseModel, create_model, Field
from dataclasses import dataclass, field


@dataclass
class ToolInfo:
    """工具信息类"""
    name: str
    description: str
    func: Callable
    args_schema: Optional[Type[BaseModel]] = None
    parameters: Dict[str, Dict] = field(default_factory=dict)
    required_params: List[str] = field(default_factory=list)

from mcp_loader.mcp_client import MCPClient

class OpenAiToolRegistry:
    def __init__(self, timeout=360):
        self._tools: Dict[str, ToolInfo] = {}
        self.clients: Dict[str, MCPClient] = {}
        self.timeout = timeout

    def register(self, tool_info: ToolInfo):
        self._tools[tool_info.name] = tool_info
    
    def get_tool(self, name: str) -> Optional[ToolInfo]:
        return self._tools.get(name)
    
    def get_all_tools(self) -> Dict[str, ToolInfo]:
        return self._tools.copy()
    
    async def add_client(self, name: str, timeout: int, transport: str, **transport_params):
        if name in self.clients:
            return self.clients[name]
        
        client = MCPClient(name, transport, **transport_params)
        await client.connect(timeout)
        self.clients[name] = client
        return client
    
    async def cleanup_all(self):
        for key in self.clients:
            await self.clients[key].cleanup()
        self.clients.clear()

    '''
    {'type': 'function', 
        'function': {
            'name': 'search_papers', 
            'description': '搜索学术论文的工具', 
            'parameters': {
                'properties': {
                    'query': {
                        'description': "查询内容，例如：'the latest research on language models'", 
                        'type': 'string'
                    }, 
                    'last_date': {
                        'description': "查询截止日期，例如：'2024-01-01'", 
                        'type': 'string'
                    }, 
                    'author': {
                        'description': "查询作者，例如：'John Doe'", 
                        'type': 'string'
                    }, 
                    'categories': {
                        'description': "arxiv类别，例如：'cs.CL, cs.AI, cs.*, math.*, etc.'", 
                        'type': 'string'
                    }
                }, 
                'required': ['query', 'last_date', 'author', 'categories'], 
                'type': 'object'
            }
        }
    }

    '''

    def get_tool_definitions(self) -> List[Dict]:
        definitions = []
        for tool_info in self._tools.values():
            definition = {
                "type": "function",
                "function": {
                    "name": tool_info.name,
                    "description": tool_info.description,
                    "parameters": {
                        "type": "object",
                        "properties": tool_info.parameters,
                        "required": tool_info.required_params
                    }
                }
            }
            definitions.append(definition)
        return definitions


# 全局工具注册器
_tool_registry = OpenAiToolRegistry()


def get_tool_registry() -> OpenAiToolRegistry:
    return _tool_registry



def extract_function_info(func: Callable) -> Dict[str, Any]:
    func_name = func.__name__
    docstring = inspect.getdoc(func) or ""
    
    # 从文档字符串中提取描述
    description = ""
    if docstring:
        # 取第一段作为描述
        lines = docstring.strip().split('\n')
        description_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                break
            description_lines.append(line)
        description = ' '.join(description_lines)
    
    return {
        "name": func_name,
        "description": description,
        "docstring": docstring
    }

import re
def create_pydantic_schema_from_function(func: Callable) -> tuple[Type[BaseModel], List[str]]:
    """从函数签名创建 Pydantic 模型
    
    返回:
        tuple: (Pydantic 模型, 必需参数列表)
    """
    signature = inspect.signature(func)
    type_hints = get_type_hints(func)
    
    # 提前解析一次文档字符串，构建参数名 -> 描述的映射
    param_descriptions = {}
    docstring = inspect.getdoc(func) or ""
    if docstring:
        # 支持 :param name: description 或 @param name: description 格式
        # 正则匹配两种风格，捕获参数名和描述
        pattern = r'(?::param|@param)\s+(\w+)\s*:\s*(.+)'
        matches = re.findall(pattern, docstring, re.MULTILINE)
        for param_name, desc in matches:
            param_descriptions[param_name] = desc.strip()
    
    fields = {}
    required_params = []
    
    for param_name, param in signature.parameters.items():
        # 跳过 self、*args、**kwargs
        if param_name == 'self':
            continue
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            # 对于 *args 和 **kwargs，暂时不支持作为工具参数，跳过并警告
            print(f"Warning: 函数 {func.__name__} 包含 *{param_name}，工具参数不支持可变参数，已忽略")
            continue
        
        # 获取参数类型
        param_type = type_hints.get(param_name, Any)
        
        # 获取描述（来自 docstring）
        description = param_descriptions.get(param_name, "")
        
        # 判断是否为必填参数（没有默认值）
        if param.default == inspect.Parameter.empty:
            # 必填参数
            field = Field(..., description=description)
            required_params.append(param_name)
        else:
            # 可选参数，使用默认值
            field = Field(default=param.default, description=description)
        
        fields[param_name] = (param_type, field)

    # 创建动态模型
    model_name = f"{func.__name__}Schema"
    return create_model(model_name, **fields), required_params


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    args_schema: Optional[Type[BaseModel]] = None,
    auto_extract: bool = True
):
    """
    Agent 工具装饰器
    
    参数:
        name: 工具名称，如果为 None 则使用函数名
        description: 工具描述，如果为 None 则从函数文档字符串中提取
        args_schema: Pydantic 参数模型，如果为 None 则自动从函数签名创建
        auto_extract: 是否自动从函数签名和文档字符串中提取信息
    
    使用示例:
        @tool
        def calculator(expression: str) -> float:
            \"\"\"执行数学计算
            
            
            :param expression: 数学表达式，如 '2 + 3 * 4'
            \"\"\"
            return eval(expression)
        
        @tool(name="file_reader", description="读取文件内容")
        def read_file(path: str) -> str:
            with open(path, 'r') as f:
                return f.read()
        
        @tool(args_schema=FileOperationSchema)
        def file_operation(operation: str, path: str, content: Optional[str] = None):
            \"\"\"文件操作\"\"\"
            ...
    """
    
    def decorator(func: Callable):
        # 提取函数信息
        func_info = extract_function_info(func)
        
        # 确定工具名称
        tool_name = name or func_info["name"]
        
        # 确定工具描述
        tool_description = description or func_info["description"]
        

        # 创建或使用参数模式
        if args_schema is not None:
            schema_model = args_schema
        elif auto_extract:
            schema_model, _ = create_pydantic_schema_from_function(func)

        else:
            schema_model = None


        parameters = {}
        required_params = []
        schema = schema_model.model_json_schema()


        parameters = schema.get("properties", {})
        for item in parameters:
            if "title" in parameters[item]:
                del parameters[item]['title']

        required_params = schema.get("required", [])
            
      
        


        timeout_seconds = _tool_registry.timeout
        if timeout_seconds is None:
            timeout_seconds = 0
        import asyncio
        async def wrapper(*args, **kwargs):
            # 1. 参数验证（如果有 schema）
            if schema_model is not None:
                model_instance = schema_model(**kwargs)
                validated_kwargs = model_instance.model_dump()
            else:
                validated_kwargs = kwargs


            # 统一用 asyncio.wait_for 包装
            try:
                if inspect.iscoroutinefunction(func):
                    # print(f"asyn start wait for {timeout_seconds}")
                    return await asyncio.wait_for(
                        func(*args, **validated_kwargs),
                        timeout=timeout_seconds
                    )
                else:
                    # 同步函数在线程池中执行，再用 wait_for 限制总时间
                    # print(f"sync start wait for {timeout_seconds}")
                    return await asyncio.wait_for(
                        asyncio.to_thread(func, *args, **validated_kwargs),
                        timeout=timeout_seconds
                    )
            except asyncio.TimeoutError:
                # print("time out")
                return {
                    "success": False,
                    "message": f"Tool execution timed out after {timeout_seconds} seconds",
                    "error": "TimeoutError"
                }
            except Exception as e:
                raise e
            
        tool_info = ToolInfo(
            name=tool_name,
            description=tool_description,
            func=wrapper,
            args_schema=schema_model,
            parameters=parameters,
            required_params=required_params
        )
        
        # 注册工具
        _tool_registry.register(tool_info)

        return wrapper
    
    # 处理 @tool 不带括号的情况
    if callable(name):
        func = name
        name = None
        return decorator(func)
    
    return decorator

