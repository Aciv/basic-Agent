from mcp import ClientSession, StdioServerParameters

from mcp.client.streamable_http import streamable_http_client

from mcp.client.stdio import stdio_client
from typing import Any, Dict, List, Optional
from contextlib import AsyncExitStack
import os
import logging

logging.basicConfig(level=logging.WARN, format="%(asctime)s - %(levelname)s - %(message)s")



os.environ["NO_PROXY"] = "localhost,127.0.0.1"


class MCPClient:

    def __init__(self, server_name: str, transport: str, **transport_params):
        """
        初始化MCP客户端
        
        Args:
            server_name: 服务器名称
            command: 服务器启动命令
            args: 服务器参数
            env: 环境变量
        """
        self.server_name = server_name
        self.transport = transport
        self.transport_params = transport_params

        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()



    async def connect(self, timeout: float = 30.0):
        """连接到MCP服务器"""
        try:
            import asyncio
            async with asyncio.timeout(timeout):
                if self.transport == "stdio":
                    # 原有 stdio 逻辑
                    server_params = StdioServerParameters(
                        command=self.transport_params["command"],
                        args=self.transport_params.get("args", []),
                        env={**os.environ, **self.transport_params["env"]} if self.transport_params.get("env") else None
                    )
                    stdio_transport = await self.exit_stack.enter_async_context(
                        stdio_client(server_params)
                    )
                    read_stream, write_stream = stdio_transport

                    
                    logging.info(f"成功连接到MCP服务器: {self.server_name} ({self.transport})")
                elif self.transport == "streamableHttp":
                    # 使用 SSE 客户端实现 streamableHttp
                    url = self.transport_params["url"]
                    
                    stream_transport = await self.exit_stack.enter_async_context(
                        streamable_http_client(url=url)
                    )
                    read_stream, write_stream, _ = stream_transport



                    logging.info(f"成功连接到MCP服务器 (HTTP POST): {self.server_name}")


                else:
                    raise ValueError(f"不支持的传输类型: {self.transport}")

                # 统一创建会话
                session = await self.exit_stack.enter_async_context(
                    ClientSession(read_stream, write_stream)
                )
                await session.initialize()
                self.session = session

        except Exception as e:
            logging.error(f"连接MCP服务器失败: {e}")
            import traceback
            traceback.print_exc()
            await self.cleanup()
            raise
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """列出服务器提供的所有工具"""
        if not self.session:
            raise
        
        try:
            tools_response = await self.session.list_tools()

            tools = []
            
            for tool in tools_response.tools:
                tool_info = {
                    "name": tool.name,
                    "description": tool.description or "",
                    "input_schema": tool.inputSchema or {}
                }
                tools.append(tool_info)
            
            return tools
            
        except Exception as e:
            logging.error(f"获取工具列表失败: {e}")
            raise
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """调用MCP工具"""
        if not self.session:
            raise RuntimeError("会话未初始化，请先调用connect()")
        
        try:
            logging.info(f"调用工具: {tool_name}, 参数: {arguments}")
            result = await self.session.call_tool(tool_name, arguments)
            return result.content
            
        except Exception as e:
            logging.error(f"调用工具失败: {e}")
            raise
    
    async def cleanup(self):
        """清理资源"""
        try:
            await self.exit_stack.aclose()
            self.session = None
            logging.info(f"已清理MCP客户端: {self.server_name}")
        except Exception as e:
            logging.warning(f"清理资源时出错: {e}")
