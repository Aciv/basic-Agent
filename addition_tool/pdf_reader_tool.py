"""
PDF阅读工具
支持从HTTP URL和本地文件读取PDF文本内容,支持分段获取
从URL下载的PDF会自动缓存到 automate_output 目录下
所有文件读取和HTTP请求均为异步操作
"""

import asyncio
import hashlib
import io
import os
import re
import tempfile
from typing import Optional, Dict, Any
from urllib.parse import urlparse

import httpx
import fitz  # PyMuPDF

from tool.tools import tool


# 缓存目录
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "automate_output", "download_pdf")


def _ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def _is_url(path: str) -> bool:
    try:
        result = urlparse(path)
        return result.scheme in ('http', 'https')
    except Exception:
        return False


def _url_to_cache_path(url: str) -> str:

    # 使用URL的哈希作为文件名,避免文件名冲突
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()

    # 从URL中提取原始文件名(如果有)
    parsed = urlparse(url)
    original_name = os.path.basename(parsed.path)
    if original_name and original_name.endswith('.pdf'):
        name_without_ext = original_name[:-4]
        return os.path.join(CACHE_DIR, f"{name_without_ext}_{url_hash}.pdf")
    else:
        return os.path.join(CACHE_DIR, f"{url_hash}.pdf")


async def _get_pdf_bytes(source: str, timeout: int = 30) -> tuple:
    """
    异步获取PDF字节数据。
    
    返回:
        tuple: (pdf_bytes, source_type, local_path)
            - pdf_bytes: PDF文件的字节数据
            - source_type: "url" 或 "local"
            - local_path: 如果是URL下载,返回本地缓存路径;如果是本地文件,返回原路径
    """
    if not _is_url(source):
        # 本地文件 - 使用 asyncio.to_thread 异步读取
        if not os.path.isfile(source):
            raise FileNotFoundError(f"本地文件不存在: {source}")
        loop = asyncio.get_running_loop()
        pdf_bytes = await loop.run_in_executor(None, _read_file_sync, source)
        return pdf_bytes, "local", source

    # URL来源
    _ensure_cache_dir()
    cache_path = _url_to_cache_path(source)

    # 如果缓存文件已存在,直接异步读取
    if os.path.isfile(cache_path):
        loop = asyncio.get_running_loop()
        pdf_bytes = await loop.run_in_executor(None, _read_file_sync, cache_path)
        return pdf_bytes, "url", cache_path

    # 异步下载并缓存
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        resp = await client.get(source)
        resp.raise_for_status()
        pdf_bytes = resp.content

    # 异步写入缓存
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _write_file_sync, cache_path, pdf_bytes)

    return pdf_bytes, "url", cache_path


def _read_file_sync(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def _write_file_sync(path: str, data: bytes):
    with open(path, "wb") as f:
        f.write(data)


def _extract_text_from_pdf(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text()
        full_text.append(text)
    doc.close()
    return "\n".join(full_text)


def _split_text_into_chunks(text: str, chunk_size: int) -> list:
    if chunk_size <= 0:
        return [text]

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + chunk_size
        if end >= text_len:
            chunks.append(text[start:])
            break

        # 尝试在换行符处分割
        newline_pos = text.rfind('\n', start, end)
        if newline_pos > start:
            end = newline_pos + 1
        else:
            # 尝试在空格处分割
            space_pos = text.rfind(' ', start, end)
            if space_pos > start:
                end = space_pos + 1

        chunks.append(text[start:end])
        start = end

    return chunks


@tool
async def read_pdf(
    source: str,
    chunk_size: int = 0,
    chunk_index: Optional[int] = None,
    page_start: Optional[int] = None,
    page_end: Optional[int] = None,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    读取PDF文件内容,支持从HTTP URL或本地文件路径读取,支持分段获取。
    从URL下载的PDF会自动缓存到 automate_output 目录,下次直接读取缓存。
    文件读取和HTTP请求均为异步操作。

    :param source: PDF来源,可以是HTTP/HTTPS URL或本地文件路径
    :param chunk_size: 每段字符数,0表示不分段(一次性返回全部文本)
    :param chunk_index: 要获取的分段索引(从0开始),为None时返回所有分段信息
    :param page_start: 起始页码(从1开始),为None时从第1页开始
    :param page_end: 结束页码(包含),为None时读取到最后一页
    :param timeout: 下载超时时间(秒),仅对URL有效,默认30秒
    :return: PDF文本内容及元数据
    """
    try:
        # 1. 异步获取PDF字节数据(自动处理URL下载和缓存)
        try:
            pdf_bytes, source_type, local_path = await _get_pdf_bytes(source, timeout)
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "message": f"下载PDF失败,HTTP状态码: {e.response.status_code}",
                "source": source,
                "error": str(e)
            }
        except httpx.TimeoutException:
            return {
                "success": False,
                "message": f"下载PDF超时({timeout}秒)",
                "source": source,
                "error": "Timeout"
            }
        except FileNotFoundError as e:
            return {
                "success": False,
                "message": str(e),
                "source": source,
                "error": "FileNotFound"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"获取PDF失败: {str(e)}",
                "source": source,
                "error": str(e)
            }

        # 2. 打开PDF文档获取基本信息
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_pages = len(doc)

        # 确定页码范围
        p_start = (page_start - 1) if page_start is not None else 0
        p_end = min(page_end, total_pages) if page_end is not None else total_pages

        if p_start < 0:
            p_start = 0
        if p_end > total_pages:
            p_end = total_pages
        if p_start >= p_end:
            doc.close()
            return {
                "success": False,
                "message": f"无效的页码范围: {page_start}-{page_end},PDF共{total_pages}页",
                "source": source,
                "total_pages": total_pages,
                "error": "InvalidPageRange"
            }

        # 3. 提取指定范围的文本
        page_texts = []
        for page_num in range(p_start, p_end):
            page = doc.load_page(page_num)
            text = page.get_text()
            page_texts.append({
                "page_number": page_num + 1,
                "text": text,
                "char_count": len(text)
            })

        doc.close()

        # 4. 合并文本
        full_text = "\n".join(pt["text"] for pt in page_texts)

        # 5. 分段处理
        if chunk_size > 0:
            chunks = _split_text_into_chunks(full_text, chunk_size)
            total_chunks = len(chunks)

            if chunk_index is not None:
                # 返回指定分段
                if chunk_index < 0 or chunk_index >= total_chunks:
                    return {
                        "success": False,
                        "message": f"分段索引 {chunk_index} 超出范围(0-{total_chunks - 1})",
                        "source": source,
                        "total_chunks": total_chunks,
                        "chunk_size": chunk_size,
                        "error": "InvalidChunkIndex"
                    }

                return {
                    "success": True,
                    "message": f"成功获取PDF分段 {chunk_index + 1}/{total_chunks}",
                    "source": source,
                    "source_type": source_type,
                    "local_path": local_path,
                    "total_pages": total_pages,
                    "page_range": f"{p_start + 1}-{p_end}",
                    "total_chunks": total_chunks,
                    "chunk_index": chunk_index,
                    "chunk_size": chunk_size,
                    "content": chunks[chunk_index],
                    "char_count": len(chunks[chunk_index])
                }
            else:
                # 返回所有分段信息
                chunk_infos = []
                for i, chunk in enumerate(chunks):
                    chunk_infos.append({
                        "chunk_index": i,
                        "char_count": len(chunk),
                        "preview": chunk[:200] + "..." if len(chunk) > 200 else chunk
                    })

                return {
                    "success": True,
                    "message": f"PDF共分为 {total_chunks} 段",
                    "source": source,
                    "source_type": source_type,
                    "local_path": local_path,
                    "total_pages": total_pages,
                    "page_range": f"{p_start + 1}-{p_end}",
                    "total_chunks": total_chunks,
                    "chunk_size": chunk_size,
                    "chunks": chunk_infos
                }
        else:
            # 不分段,返回全部文本
            return {
                "success": True,
                "message": f"成功读取PDF内容(共{total_pages}页)",
                "source": source,
                "source_type": source_type,
                "local_path": local_path,
                "total_pages": total_pages,
                "page_range": f"{p_start + 1}-{p_end}",
                "content": full_text,
                "char_count": len(full_text),
                "page_details": page_texts
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"读取PDF时发生错误: {str(e)}",
            "source": source,
            "error": str(e)
        }


@tool
async def get_pdf_info(source: str, timeout: int = 30) -> Dict[str, Any]:
    """
    获取PDF文件的元数据信息(不提取文本内容)。
    从URL下载的PDF会自动缓存到 automate_output 目录,下次直接读取缓存。
    文件读取和HTTP请求均为异步操作。

    :param source: PDF来源,可以是HTTP/HTTPS URL或本地文件路径
    :param timeout: 下载超时时间(秒),仅对URL有效,默认30秒
    :return: PDF元数据信息
    """
    try:
        # 异步获取PDF字节数据(自动处理URL下载和缓存)
        try:
            pdf_bytes, source_type, local_path = await _get_pdf_bytes(source, timeout)
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "message": f"下载PDF失败,HTTP状态码: {e.response.status_code}",
                "source": source,
                "error": str(e)
            }
        except httpx.TimeoutException:
            return {
                "success": False,
                "message": f"下载PDF超时({timeout}秒)",
                "source": source,
                "error": "Timeout"
            }
        except FileNotFoundError as e:
            return {
                "success": False,
                "message": str(e),
                "source": source,
                "error": "FileNotFound"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"获取PDF失败: {str(e)}",
                "source": source,
                "error": str(e)
            }

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        metadata = doc.metadata or {}
        total_pages = len(doc)

        # 获取每页基本信息
        page_sizes = []
        for page_num in range(total_pages):
            page = doc.load_page(page_num)
            rect = page.rect
            page_sizes.append({
                "page_number": page_num + 1,
                "width": round(rect.width, 1),
                "height": round(rect.height, 1)
            })

        doc.close()

        return {
            "success": True,
            "message": f"PDF信息获取成功(共{total_pages}页)",
            "source": source,
            "source_type": source_type,
            "local_path": local_path,
            "total_pages": total_pages,
            "file_size_bytes": len(pdf_bytes),
            "metadata": {
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "subject": metadata.get("subject", ""),
                "keywords": metadata.get("keywords", ""),
                "producer": metadata.get("producer", ""),
                "creator": metadata.get("creator", ""),
                "creation_date": metadata.get("creationDate", ""),
                "modification_date": metadata.get("modDate", "")
            },
            "page_sizes": page_sizes
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"获取PDF信息时发生错误: {str(e)}",
            "source": source,
            "error": str(e)
        }


