"""
基础工具初始化模块
提供文件读写、修改、执行命令等基础工具
"""

import os
import subprocess
import sys
from typing import Optional, Dict, Any
from pathlib import Path

from tool.tools import tool
from datetime import datetime
@tool
def get_time():
    """
    获取当前事件，在涉及时间相关操作一定要执行这个工具获取真正的时间
    """
    return str(datetime.now())

@tool
def write_file(
    path: str,
    content: str,
    encoding: str = "utf-8"
) -> Dict[str, Any]:
    """
    写入文件工具,将内容写入指定路径的文件。如果文件不存在则创建,如果存在则覆盖。
    
    :param path: 文件路径,可以是相对路径或绝对路径
    :param content: 要写入文件的内容
    :param encoding: 文件编码,默认为 utf-8
    :return: 操作结果信息
    """
    try:
        # 确保目录存在
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入文件
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)
        
        return {
            "success": True,
            "message": f"文件已成功写入: {path}",
            "path": str(file_path.absolute()),
            "size": len(content)
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"写入文件失败: {str(e)}",
            "path": path,
            "error": str(e)
        }


@tool
def read_file(
    path: str,
    encoding: str = "utf-8",
    start_line: Optional[int] = None,
    end_line: Optional[int] = None
) -> Dict[str, Any]:
    """
    读取文件工具,读取指定路径的文件内容。可以指定读取的起始行和结束行。
    
    :param path: 文件路径,可以是相对路径或绝对路径
    :param encoding: 文件编码,默认为 utf-8
    :param start_line: 起始行号(1-based),如果为 None 则从开头读取
    :param end_line: 结束行号(1-based),如果为 None 则读取到文件末尾
    :return: 文件内容及元数据
    """
    try:
        file_path = Path(path)
        
        if not file_path.exists():
            return {
                "success": False,
                "message": f"文件不存在: {path}",
                "path": str(file_path.absolute())
            }
        
        if not file_path.is_file():
            return {
                "success": False,
                "message": f"路径不是文件: {path}",
                "path": str(file_path.absolute())
            }
        
        # 读取文件
        with open(file_path, 'r', encoding=encoding) as f:
            lines = f.readlines()
        
        # 处理行范围
        if start_line is not None:
            start_idx = max(0, start_line - 1)
        else:
            start_idx = 0
            
        if end_line is not None:
            end_idx = min(len(lines), end_line)
        else:
            end_idx = len(lines)
        
        selected_lines = lines[start_idx:end_idx]
        content = ''.join(selected_lines)
        
        return {
            "success": True,
            "message": f"文件读取成功: {path}",
            "path": str(file_path.absolute()),
            "content": content,
            "total_lines": len(lines),
            "read_lines": len(selected_lines),
            "start_line": start_idx + 1 if selected_lines else 0,
            "end_line": end_idx if selected_lines else 0,
            "size": os.path.getsize(file_path)
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"读取文件失败: {str(e)}",
            "path": path,
            "error": str(e)
        }


@tool
def modify_file(
    path: str,
    search_pattern: str,
    replace_with: str,
    encoding: str = "utf-8",
    replace_all: bool = False
) -> Dict[str, Any]:
    """
    修改文件工具,在文件中搜索指定模式并替换为新的内容。
    
    :param path: 文件路径,可以是相对路径或绝对路径
    :param search_pattern: 要搜索的文本模式
    :param replace_with: 替换为的文本
    :param encoding: 文件编码,默认为 utf-8
    :param replace_all: 是否替换所有匹配项,如果为 False 则只替换第一个匹配项
    :return: 操作结果信息
    """
    try:
        file_path = Path(path)
        
        if not file_path.exists():
            return {
                "success": False,
                "message": f"文件不存在: {path}",
                "path": str(file_path.absolute())
            }
        
        if not file_path.is_file():
            return {
                "success": False,
                "message": f"路径不是文件: {path}",
                "path": str(file_path.absolute())
            }
        
        # 读取文件内容
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()
        
        # 执行替换
        if replace_all:
            new_content = content.replace(search_pattern, replace_with)
            replacements = content.count(search_pattern)
        else:
            new_content = content.replace(search_pattern, replace_with, 1)
            replacements = 1 if search_pattern in content else 0
        
        # 如果没有匹配项
        if replacements == 0:
            return {
                "success": False,
                "message": f"未找到匹配的模式: {search_pattern}",
                "path": str(file_path.absolute()),
                "replacements": 0
            }
        
        # 写入修改后的内容
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(new_content)
        
        return {
            "success": True,
            "message": f"文件修改成功: {path}",
            "path": str(file_path.absolute()),
            "replacements": replacements,
            "original_size": len(content),
            "new_size": len(new_content)
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"修改文件失败: {str(e)}",
            "path": path,
            "error": str(e)
        }


@tool
def execute_command(
    command: str,
    working_directory: Optional[str] = None,
    timeout: Optional[int] = 30
) -> Dict[str, Any]:
    """
    执行命令工具,在指定工作目录中执行 shell 命令。
    
    :param command: 要执行的命令
    :param working_directory: 工作目录,如果为 None 则使用当前目录
    :param timeout: 命令执行超时时间(秒),如果为 None 则不超时
    :return: 命令执行结果
    """
    try:
        # 设置工作目录
        cwd = working_directory if working_directory else os.getcwd()
        
        # 执行命令
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8',
            errors='ignore'
        )
        
        return {
            "success": True,
            "message": f"命令执行完成: {command}",
            "command": command,
            "working_directory": cwd,
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timed_out": False
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": f"命令执行超时: {command}",
            "command": command,
            "working_directory": working_directory or os.getcwd(),
            "return_code": None,
            "stdout": "",
            "stderr": "",
            "timed_out": True
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"命令执行失败: {str(e)}",
            "command": command,
            "working_directory": working_directory or os.getcwd(),
            "return_code": None,
            "stdout": "",
            "stderr": str(e),
            "timed_out": False,
            "error": str(e)
        }


@tool
def list_files(
    path: str = ".",
    recursive: bool = False
) -> Dict[str, Any]:
    """
    列出文件工具,列出指定目录中的文件和子目录。
    
    :param path: 目录路径,默认为当前目录
    :param recursive: 是否递归列出子目录
    :return: 目录列表结果
    """
    try:
        dir_path = Path(path)
        
        if not dir_path.exists():
            return {
                "success": False,
                "message": f"目录不存在: {path}",
                "path": str(dir_path.absolute())
            }
        
        if not dir_path.is_dir():
            return {
                "success": False,
                "message": f"路径不是目录: {path}",
                "path": str(dir_path.absolute())
            }
        
        files = []
        directories = []
        
        if recursive:
            # 递归列出
            for root, dirs, filenames in os.walk(dir_path):
                root_path = Path(root)
                rel_root = root_path.relative_to(dir_path) if root_path != dir_path else Path(".")
                
                for dirname in dirs:
                    directories.append(str(rel_root / dirname))
                
                for filename in filenames:
                    files.append(str(rel_root / filename))
        else:
            # 仅列出当前目录
            for item in dir_path.iterdir():
                if item.is_file():
                    files.append(item.name)
                elif item.is_dir():
                    directories.append(item.name)
        
        return {
            "success": True,
            "message": f"目录列表成功: {path}",
            "path": str(dir_path.absolute()),
            "files": sorted(files),
            "directories": sorted(directories),
            "total_files": len(files),
            "total_directories": len(directories),
            "recursive": recursive
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"列出文件失败: {str(e)}",
            "path": path,
            "error": str(e)
        }


@tool
def file_info(
    path: str
) -> Dict[str, Any]:
    """
    获取文件信息工具,获取指定路径的文件或目录的详细信息。
    
    :param path: 文件或目录路径
    :return: 文件/目录信息
    """
    try:
        item_path = Path(path)
        
        if not item_path.exists():
            return {
                "success": False,
                "message": f"路径不存在: {path}",
                "path": str(item_path.absolute())
            }
        
        stats = item_path.stat()
        
        info = {
            "success": True,
            "message": f"文件信息获取成功: {path}",
            "path": str(item_path.absolute()),
            "exists": True,
            "is_file": item_path.is_file(),
            "is_dir": item_path.is_dir(),
            "size": stats.st_size if item_path.is_file() else 0,
            "created": stats.st_birthtime,
            "modified": stats.st_mtime,
            "accessed": stats.st_atime,
            "permissions": oct(stats.st_mode)[-3:],
            "absolute_path": str(item_path.absolute())
        }
        
        return info
    except Exception as e:
        return {
            "success": False,
            "message": f"获取文件信息失败: {str(e)}",
            "path": path,
            "error": str(e)
        }


@tool
def file_info(
    path: str
) -> Dict[str, Any]:
    """
    获取文件信息工具,获取指定路径的文件或目录的详细信息。
    
    :param path: 文件或目录路径
    :return: 文件/目录信息
    """
    try:
        item_path = Path(path)
        
        if not item_path.exists():
            return {
                "success": False,
                "message": f"路径不存在: {path}",
                "path": str(item_path.absolute())
            }
        
        stats = item_path.stat()
        
        info = {
            "success": True,
            "message": f"文件信息获取成功: {path}",
            "path": str(item_path.absolute()),
            "exists": True,
            "is_file": item_path.is_file(),
            "is_dir": item_path.is_dir(),
            "size": stats.st_size if item_path.is_file() else 0,
            "created": stats.st_birthtime,
            "modified": stats.st_mtime,
            "accessed": stats.st_atime,
            "permissions": oct(stats.st_mode)[-3:],
            "absolute_path": str(item_path.absolute())
        }
        
        return info
    except Exception as e:
        return {
            "success": False,
            "message": f"获取文件信息失败: {str(e)}",
            "path": path,
            "error": str(e)
        }
    

__all__ = [
    'write_file',
    'read_file',
    'modify_file',
    'execute_command',
    'list_files',
    'file_info'
]