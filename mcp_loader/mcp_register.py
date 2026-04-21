import os
from tool.tools import ToolInfo, get_tool_registry

tools_manager = get_tool_registry()


import json
async def get_mcp_server(path : str):
    with open(path, 'r') as mcp_configs:
        data = json.load(mcp_configs)

        for mcp_name in data['mcpServers']:

            if data['mcpServers'][mcp_name].get('disabled', False):
                continue
            if data['mcpServers'][mcp_name].get('type', 'stdio') == 'stdio':

                await server_register(name=mcp_name, 
                        timeout=data['mcpServers'][mcp_name].get('timeout', 60),
                        transport=data['mcpServers'][mcp_name].get('type', 'stdio'),
                        command=data['mcpServers'][mcp_name].get('command', ""),
                        args=data['mcpServers'][mcp_name].get('args', ""),
                    )
            else:
                await server_register(name=mcp_name, 
                        timeout=data['mcpServers'][mcp_name].get('timeout', 60),
                        transport=data['mcpServers'][mcp_name].get('type', 'streamableHttp'),
                        url=data['mcpServers'][mcp_name].get('url', ""),
                    )



def make_tool_func(client, tool_name):
    async def wrapper(**kwargs):
        return await client.call_tool(tool_name=tool_name, arguments=kwargs)
    return wrapper

async def server_register(name: str, timeout : int, transport: str, **transport_params):
    try:
        # 添加文件系统服务器（需要Node.js和npx）
        print("正在连接文件系统MCP服务器...")


        client = await tools_manager.add_client(
            name=name,
            timeout=timeout,
            transport=transport,
            **transport_params
        )

        tools = await client.list_tools()


        for tool in tools:

            tool_info = ToolInfo(
                name=tool['name'],
                description=tool.get('description', ""),
                func=make_tool_func(client, tool['name']),
                args_schema=None,
                parameters=tool['input_schema'].get('properties', {}),
                required_params=tool['input_schema'].get('required', [])
            )

            tools_manager.register(tool_info)

    except Exception as e:
        print(f"注册mcp服务器失败: {e}")

