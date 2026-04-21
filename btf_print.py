import logging
from dataclasses import fields, is_dataclass
from typing import Any, Callable, Dict, List, Optional, Union


class LogPrinter:
    """使用 logging 输出格式化对象，每次直接输出一行（不支持 end=''）"""

    def __init__(self, logger: Optional[logging.Logger] = None, level: int = logging.INFO):
        self.logger = logger or logging.getLogger()
        self.level = level
        self._handlers: Dict[type, Callable] = {}
        self._register_builtin_handlers()

    def _log_line(self, text: str, indents: int = 0):
        """输出一行缩进后的文本"""
        if text is None:
            text = ""
        self.logger.log(self.level, " " * indents + text)

    def _register_builtin_handlers(self):
        self.register_handler(str, self._print_str)
        self.register_handler(list, self._print_list)
        self.register_handler(dict, self._print_dict)
        self._dataclass_handler = self._print_dataclass

    def register_handler(self, typ: type, handler: Callable):
        self._handlers[typ] = handler

    def _print_str(self, obj: str, indents: int):
        for line in obj.split('\n'):
            self._log_line(line, indents)

    def _print_dataclass(self, obj: Any, indents: int):
        for field in fields(obj):
            name = field.name
            value = getattr(obj, name)
            # 先输出字段名（不换行在 logging 中无法实现，改为单独一行）
            self._log_line(f"{name}:", indents)
            need_indent = (
                isinstance(value, (list, dict)) or
                is_dataclass(value) or
                (isinstance(value, str) and '\n' in value)
            )
            if need_indent:
                self.print(value, indents + 2)
            else:
                self._log_line(str(value), indents + 2)

    def _print_list(self, obj: List, indents: int):
        self._log_line("[", indents)
        for elem in obj:
            self.print(elem, indents + 2)
        self._log_line("]", indents)

    def _print_dict(self, obj: Dict, indents: int):
        for key, value in obj.items():
            self._log_line(f"{key}:", indents)
            need_indent = (
                isinstance(value, (list, dict)) or
                is_dataclass(value) or
                (isinstance(value, str) and '\n' in value)
            )
            if need_indent:
                self.print(value, indents + 2)
            else:
                self._log_line(str(value), indents + 2)

    def print(self, obj: Any, indents: int = 0):
        obj_type = type(obj)
        if obj_type in self._handlers:
            self._handlers[obj_type](obj, indents)
        elif is_dataclass(obj):
            self._dataclass_handler(obj, indents)
        else:
            self._log_line(str(obj), indents)

    def close(self):
        pass  # 兼容旧接口