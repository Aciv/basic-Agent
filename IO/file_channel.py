import asyncio
import json
import os
import sys
from typing import Optional
from IO.channel_base import InputChannel, OutputChannel, TransportMessage


class FileInChannel(InputChannel):
    """
    文件输入通道：定期从指定文件读取消息，放入输入队列。
    
    类似 StdInChannel 从 stdin 读取，FileInChannel 从文件读取消息。
    支持 JSON 格式和纯文本格式。
    """

    def __init__(self, input_queue: asyncio.Queue,
                 file_path: str,
                 output_name: Optional[str] = "FileOutput",
                 error_name: Optional[str] = "FileOutput",
                 name: str = "FileInput",
                 poll_interval: float = 0.5,
                 delete_after_read: bool = False,
                 encoding: str = "utf-8",
                 semaphore: Optional[asyncio.Semaphore] = None):
        """
        :param file_path: 要读取的文件路径
        :param poll_interval: 轮询间隔（秒）
        :param delete_after_read: 读取后是否删除文件
        :param encoding: 文件编码
        """
        super().__init__(input_queue=input_queue, output_name=output_name,
                         name=name, error_name=error_name,
                         semaphore=semaphore, poll_interval=poll_interval)
        self.file_path = file_path
        self.delete_after_read = delete_after_read
        self.encoding = encoding

    async def _read(self) -> Optional[TransportMessage]:
        if not os.path.exists(self.file_path):
            return None

        try:
            loop = asyncio.get_running_loop()

            def read_file():
                with open(self.file_path, "r", encoding=self.encoding) as f:
                    return f.read()

            content = await loop.run_in_executor(None, read_file)

            if not content or content.strip() == "":
                return None

            content = content.strip()

            # 尝试解析 JSON 格式
            # 支持：{"content": "...", "context_id": "..."} 或纯文本
            try:
                data = json.loads(content)
                if isinstance(data, dict) and "content" in data:
                    text = data["content"]
                    context_id = data.get("context_id", self.name)
                else:
                    text = content
                    context_id = self.name
            except json.JSONDecodeError:
                text = content
                context_id = self.name

            # 如果删除文件，读取后删除
            if self.delete_after_read:
                def delete_file():
                    os.remove(self.file_path)
                await loop.run_in_executor(None, delete_file)

            return TransportMessage(
                context_id=context_id,
                output_id=self.output_name,
                content=text
            )

        except Exception as e:
            raise


class FileOutChannel(OutputChannel):
    def __init__(self, output_queue: asyncio.Queue,
                 file_path: str,
                 name: str = "FileOutput",
                 mode: str = "a",
                 encoding: str = "utf-8",
                 format: str = "text",
                 semaphore: Optional[asyncio.Semaphore] = None,
                 include_context_id: bool = False):
        """
        :param file_path: 输出文件路径
        :param mode: 写入模式，"a" 追加，"w" 覆盖
        :param encoding: 文件编码
        :param format: 输出格式，"text" 纯文本，"json" JSON 格式
        :param include_context_id: JSON 格式时是否包含 context_id
        """
        super().__init__(output_queue=output_queue, name=name,
                         semaphore=semaphore)
        self.file_path = file_path
        self.mode = mode
        self.encoding = encoding
        self.format = format.lower()
        self.include_context_id = include_context_id

    async def _write(self, data: TransportMessage) -> None:
        if data.content is None:
            return

        loop = asyncio.get_running_loop()

        def write_file():
            os.makedirs(os.path.dirname(os.path.abspath(self.file_path)), exist_ok=True)

            with open(self.file_path, self.mode, encoding=self.encoding) as f:
                if self.format == "json":
                    payload = {"content": data.content}
                    if self.include_context_id:
                        payload["context_id"] = data.context_id
                    f.write(json.dumps(payload, ensure_ascii=False) + "\n")
                else:
                    f.write(data.content + "\n")

        try:
            await loop.run_in_executor(None, write_file)
        except Exception as e:
            raise
