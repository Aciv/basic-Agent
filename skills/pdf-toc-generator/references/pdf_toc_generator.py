"""
PDF目录自动生成器 - 参考实现
基于 PyMuPDF (fitz) 库，自动识别PDF中的标题结构并生成目录

使用方法：
    python pdf_toc_generator.py <pdf_path> [--output <output_path>] [--format markdown|json|text]

依赖：
    pip install pymupdf
"""

import fitz  # PyMuPDF
import json
import re
import os
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class TocEntry:
    """目录条目"""
    level: int               # 目录层级（1-based）
    title: str               # 标题文本
    page_num: int            # 页码（1-based）
    y_pos: float             # 在页面中的y坐标
    font_size: float         # 字体大小
    is_bold: bool = False    # 是否粗体
    children: List['TocEntry'] = field(default_factory=list)


class PDFTocGenerator:
    """PDF目录生成器"""
    
    # 常见标题编号模式
    CHAPTER_PATTERNS = [
        r'^(?:第\s*[一二三四五六七八九十百千\d]+\s*[章章节篇部]|[Cc]hapter\s+\d+)',  # 第1章 / Chapter 1
        r'^\d+(?:\.\d+)*\s+',           # 1. / 1.1 / 1.1.1
        r'^[IVXLCDM]+\.\s+',            # I. / II. / III.
        r'^[A-Z]\.\s+',                 # A. / B. / C.
        r'^\d+\.\s+',                   # 1. / 2. / 3.
    ]
    
    # 需要过滤的内容模式（页眉、页脚、页码等）
    FILTER_PATTERNS = [
        r'^\d+$',                       # 纯数字（页码）
        r'^\s*$',                       # 空白
        r'^www\.',                      # 网址
        r'^http',                       # HTTP链接
        r'^参考文献$',                   # 参考文献
        r'^[Rr]eferences$',            # References
        r'^附录',                       # 附录
    ]
    
    def __init__(self, pdf_path: str, heading_ratio_threshold: float = 1.2):
        """
        初始化
        
        Args:
            pdf_path: PDF文件路径
            heading_ratio_threshold: 标题与正文字体大小的比例阈值，默认1.2倍
        """
        self.pdf_path = pdf_path
        self.heading_ratio_threshold = heading_ratio_threshold
        self.doc = None
        self.total_pages = 0
        self.body_font_size = 0  # 正文基准字体大小
        self.candidates = []     # 候选标题列表
        self.toc_tree = []       # 目录树
        
    def open_pdf(self) -> bool:
        """打开PDF文件"""
        try:
            self.doc = fitz.open(self.pdf_path)
            self.total_pages = len(self.doc)
            print(f"[✓] 成功打开PDF: {os.path.basename(self.pdf_path)}")
            print(f"    总页数: {self.total_pages}")
            return True
        except Exception as e:
            print(f"[✗] 打开PDF失败: {e}")
            return False
    
    def extract_text_blocks(self) -> List[dict]:
        """
        提取所有页面的文本块信息
        
        Returns:
            所有文本块列表，每个块包含位置、字体大小、文本内容等信息
        """
        all_blocks = []
        
        for page_num in range(self.total_pages):
            page = self.doc[page_num]
            # 获取页面文本块的详细字典信息
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if block["type"] != 0:  # 只处理文本块
                    continue
                    
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if not text:
                            continue
                            
                        block_info = {
                            "text": text,
                            "font_size": span["size"],
                            "font_name": span["font"],
                            "is_bold": bool(span["flags"] & 2**4),
                            "is_italic": bool(span["flags"] & 2**6),
                            "color": span["color"],
                            "bbox": span["bbox"],
                            "page_num": page_num + 1,  # 1-based
                            "y_pos": span["bbox"][1],   # y0坐标
                        }
                        all_blocks.append(block_info)
                        
        return all_blocks
    
    def analyze_font_size_distribution(self, blocks: List[dict]) -> float:
        """
        分析字体大小分布，确定正文基准字体大小
        
        Args:
            blocks: 文本块列表
            
        Returns:
            正文基准字体大小
        """
        # 统计所有字体大小
        font_sizes = defaultdict(int)
        for block in blocks:
            size = round(block["font_size"], 1)
            font_sizes[size] += 1
        
        if not font_sizes:
            return 12.0  # 默认值
        
        # 按出现频率降序排序
        sorted_sizes = sorted(font_sizes.items(), key=lambda x: -x[1])
        
        # 出现频率最高的字体大小通常为正文
        # 但需要排除非常小的字体（可能是注释或页脚）
        for size, count in sorted_sizes:
            if size >= 8:  # 排除过小的字体
                print(f"    正文基准字体大小: {size}pt (出现{count}次)")
                return size
        
        return sorted_sizes[0][0]
    
    def is_heading_pattern(self, text: str) -> bool:
        """检查文本是否匹配标题编号模式"""
        for pattern in self.CHAPTER_PATTERNS:
            if re.match(pattern, text):
                return True
        return False
    
    def should_filter(self, text: str) -> bool:
        """检查是否应该过滤该文本"""
        for pattern in self.FILTER_PATTERNS:
            if re.match(pattern, text):
                return True
        return False
    
    def detect_headings(self, blocks: List[dict]) -> List[dict]:
        """
        检测所有候选标题
        
        Args:
            blocks: 所有文本块
            
        Returns:
            候选标题列表
        """
        self.body_font_size = self.analyze_font_size_distribution(blocks)
        candidates = []
        
        for block in blocks:
            text = block["text"]
            font_size = block["font_size"]
            
            # 过滤短文本和噪声
            if len(text) < 2 or len(text) > 200:
                continue
                
            # 过滤页眉页脚
            if self.should_filter(text):
                continue
            
            # 判断是否为标题
            is_heading = False
            reasons = []
            
            # 1. 字体大小特征
            if font_size >= self.body_font_size * self.heading_ratio_threshold:
                is_heading = True
                reasons.append(f"字体大小({font_size}pt > {self.body_font_size}pt)")
            
            # 2. 粗体特征
            if block["is_bold"] and font_size >= self.body_font_size * 1.05:
                is_heading = True
                reasons.append(f"粗体+字体({font_size}pt)")
            
            # 3. 标题编号模式
            if self.is_heading_pattern(text):
                is_heading = True
                reasons.append("匹配标题编号模式")
            
            if is_heading:
                candidates.append({
                    **block,
                    "detect_reasons": reasons
                })
        
        # 按页码和y坐标排序
        candidates.sort(key=lambda x: (x["page_num"], x["y_pos"]))
        
        print(f"    检测到 {len(candidates)} 个候选标题")
        return candidates
    
    def determine_levels(self, candidates: List[dict]) -> List[dict]:
        """
        确定每个候选标题的层级
        
        Args:
            candidates: 候选标题列表
            
        Returns:
            带有层级信息的标题列表
        """
        if not candidates:
            return []
        
        # 收集所有独特的字体大小
        unique_sizes = sorted(set(c["font_size"] for c in candidates), reverse=True)
        
        # 根据字体大小分配层级
        size_to_level = {}
        for i, size in enumerate(unique_sizes):
            size_to_level[size] = i + 1  # 从1开始
        
        # 限制最大层级为6
        max_level = min(len(unique_sizes), 6)
        
        result = []
        prev_level = 1
        
        for cand in candidates:
            raw_level = size_to_level[cand["font_size"]]
            
            # 平滑处理：防止层级跳跃过大
            level = min(raw_level, prev_level + 1)
            level = min(level, max_level)
            
            # 如果标题匹配编号模式，尝试从编号推断层级
            text = cand["text"]
            match = re.match(r'^(\d+)\.', text)
            if match:
                num = int(match.group(1))
                if num > 0 and num <= 20:  # 合理范围内
                    # 检查是否有子节编号
                    if re.match(r'^\d+\.\d+', text):
                        level = max(level, 2)
                    if re.match(r'^\d+\.\d+\.\d+', text):
                        level = max(level, 3)
            
            cand["level"] = level
            prev_level = level
            result.append(cand)
        
        return result
    
    def build_toc_tree(self, entries: List[dict]) -> List[TocEntry]:
        """
        构建目录树
        
        Args:
            entries: 带层级的标题列表
            
        Returns:
            目录树（TocEntry列表）
        """
        if not entries:
            return []
        
        # 转换为TocEntry对象
        toc_entries = []
        for entry in entries:
            toc_entries.append(TocEntry(
                level=entry["level"],
                title=entry["text"],
                page_num=entry["page_num"],
                y_pos=entry["y_pos"],
                font_size=entry["font_size"],
                is_bold=entry["is_bold"],
            ))
        
        # 构建树结构
        root = []
        stack = []  # 用于追踪父节点
        
        for entry in toc_entries:
            # 找到合适的父节点
            while stack and stack[-1].level >= entry.level:
                stack.pop()
            
            if stack:
                stack[-1].children.append(entry)
            else:
                root.append(entry)
            
            stack.append(entry)
        
        return root
    
    def generate_markdown_toc(self, toc_tree: List[TocEntry], indent: int = 0) -> str:
        """
        生成Markdown格式的目录
        
        Args:
            toc_tree: 目录树
            indent: 缩进层级
            
        Returns:
            Markdown格式的目录字符串
        """
        lines = []
        for entry in toc_tree:
            # 生成缩进
            prefix = "#" * (entry.level + 1)  # H2开始
            title_text = entry.title
            # 清理标题中的换行和多余空格
            title_text = ' '.join(title_text.split())
            
            line = f"{prefix} {title_text} .................... {entry.page_num}"
            lines.append(line)
            
            # 递归处理子标题
            if entry.children:
                lines.append(self.generate_markdown_toc(entry.children, indent + 1))
        
        return '\n'.join(lines)
    
    def generate_text_toc(self, toc_tree: List[TocEntry], indent: int = 0) -> str:
        """
        生成纯文本格式的目录
        
        Args:
            toc_tree: 目录树
            indent: 缩进层级
            
        Returns:
            纯文本格式的目录字符串
        """
        lines = []
        indent_str = "  " * indent
        
        for entry in toc_tree:
            title_text = ' '.join(entry.title.split())
            # 计算填充点数
            dots = "." * max(3, 60 - len(title_text) - len(indent_str) - 5)
            line = f"{indent_str}{title_text} {dots} {entry.page_num}"
            lines.append(line)
            
            if entry.children:
                lines.append(self.generate_text_toc(entry.children, indent + 1))
        
        return '\n'.join(lines)
    
    def generate_json_toc(self, toc_tree: List[TocEntry]) -> list:
        """
        生成JSON格式的目录
        
        Args:
            toc_tree: 目录树
            
        Returns:
            JSON兼容的列表
        """
        result = []
        for entry in toc_tree:
            item = {
                "level": entry.level,
                "title": ' '.join(entry.title.split()),
                "page": entry.page_num,
            }
            if entry.children:
                item["children"] = self.generate_json_toc(entry.children)
            result.append(item)
        return result
    
    def generate_full_report(self, format: str = "markdown") -> str:
        """
        生成完整的目录报告
        
        Args:
            format: 输出格式（markdown / text / json）
            
        Returns:
            报告字符串
        """
        from datetime import datetime
        
        filename = os.path.basename(self.pdf_path)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 统计信息
        total_entries = self._count_entries(self.toc_tree)
        max_level = self._get_max_level(self.toc_tree)
        
        if format == "json":
            return json.dumps({
                "file": filename,
                "generated_at": timestamp,
                "total_pages": self.total_pages,
                "total_entries": total_entries,
                "max_level": max_level,
                "body_font_size": self.body_font_size,
                "toc": self.generate_json_toc(self.toc_tree)
            }, ensure_ascii=False, indent=2)
        
        # Markdown或纯文本格式
        lines = []
        lines.append(f"# 📑 {filename} - 自动生成目录")
        lines.append("")
        lines.append(f"> 生成时间：{timestamp}")
        lines.append(f"> 总页数：{self.total_pages}页 | 目录条目数：{total_entries}条 | 检测层级：{max_level}级")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        if format == "text":
            lines.append("目录")
            lines.append("=" * 70)
            lines.append("")
            lines.append(self.generate_text_toc(self.toc_tree))
        else:
            lines.append("## 目录")
            lines.append("")
            lines.append(self.generate_markdown_toc(self.toc_tree))
        
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## 生成说明")
        lines.append("")
        lines.append(f"- **识别方法**：基于字体大小、样式和位置特征自动识别标题")
        lines.append(f"- **检测层级**：共检测到 {max_level} 级标题层次")
        lines.append(f"- **正文基准字体**：{self.body_font_size}pt")
        
        # 评估置信度
        confidence = self._evaluate_confidence()
        lines.append(f"- **置信度**：{confidence}")
        lines.append("")
        
        return '\n'.join(lines)
    
    def _count_entries(self, tree: List[TocEntry]) -> int:
        """统计目录条目总数"""
        count = len(tree)
        for entry in tree:
            count += self._count_entries(entry.children)
        return count
    
    def _get_max_level(self, tree: List[TocEntry]) -> int:
        """获取最大层级"""
        max_level = 0
        for entry in tree:
            max_level = max(max_level, entry.level)
            if entry.children:
                max_level = max(max_level, self._get_max_level(entry.children))
        return max_level
    
    def _evaluate_confidence(self) -> str:
        """评估目录质量置信度"""
        total_entries = self._count_entries(self.toc_tree)
        
        if total_entries == 0:
            return "低（未检测到标题）"
        
        # 检查是否有标题编号模式
        numbered_count = 0
        for entry in self._flatten_tree(self.toc_tree):
            if self.is_heading_pattern(entry.title):
                numbered_count += 1
        
        ratio = numbered_count / total_entries if total_entries > 0 else 0
        
        if ratio > 0.7 and total_entries > 5:
            return "高"
        elif ratio > 0.3 and total_entries > 3:
            return "中"
        else:
            return "中低"
    
    def _flatten_tree(self, tree: List[TocEntry]) -> List[TocEntry]:
        """将目录树展平为列表"""
        result = []
        for entry in tree:
            result.append(entry)
            if entry.children:
                result.extend(self._flatten_tree(entry.children))
        return result
    
    def process(self) -> bool:
        """
        执行完整的目录生成流程
        
        Returns:
            是否成功
        """
        # 1. 打开PDF
        if not self.open_pdf():
            return False
        
        # 2. 提取文本块
        print("[*] 正在提取文本信息...")
        blocks = self.extract_text_blocks()
        print(f"    提取到 {len(blocks)} 个文本块")
        
        # 3. 检测标题
        print("[*] 正在检测标题...")
        self.candidates = self.detect_headings(blocks)
        
        # 4. 确定层级
        print("[*] 正在确定标题层级...")
        entries = self.determine_levels(self.candidates)
        
        # 5. 构建目录树
        print("[*] 正在构建目录树...")
        self.toc_tree = self.build_toc_tree(entries)
        
        total = self._count_entries(self.toc_tree)
        levels = self._get_max_level(self.toc_tree)
        print(f"[✓] 目录生成完成！共 {total} 个条目，{levels} 级层次")
        
        return True
    
    def save_output(self, output_path: str, format: str = "markdown"):
        """
        保存输出文件
        
        Args:
            output_path: 输出文件路径
            format: 输出格式
        """
        report = self.generate_full_report(format)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"[✓] 目录已保存至: {output_path}")
    
    def close(self):
        """关闭PDF文档"""
        if self.doc:
            self.doc.close()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="PDF目录自动生成器")
    parser.add_argument("pdf_path", help="PDF文件路径")
    parser.add_argument("--output", "-o", help="输出文件路径（默认自动生成）")
    parser.add_argument("--format", "-f", choices=["markdown", "text", "json"], 
                        default="markdown", help="输出格式（默认markdown）")
    parser.add_argument("--threshold", "-t", type=float, default=1.2,
                        help="标题字体大小阈值倍数（默认1.2）")
    
    args = parser.parse_args()
    
    # 检查文件是否存在
    if not os.path.exists(args.pdf_path):
        print(f"[✗] 文件不存在: {args.pdf_path}")
        return
    
    # 创建生成器
    generator = PDFTocGenerator(args.pdf_path, args.threshold)
    
    # 执行处理
    if not generator.process():
        print("[✗] 目录生成失败")
        return
    
    # 确定输出路径
    if args.output:
        output_path = args.output
    else:
        base_name = os.path.splitext(os.path.basename(args.pdf_path))[0]
        ext_map = {"markdown": ".md", "text": ".txt", "json": ".json"}
        output_path = f"automate_output/{base_name}_toc{ext_map[args.format]}"
    
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    
    # 保存输出
    generator.save_output(output_path, args.format)
    
    # 关闭文档
    generator.close()
    
    print("\n[✓] 处理完成！")


if __name__ == "__main__":
    main()
