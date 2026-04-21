"""
Additional tools module
包含额外的工具函数，如arxiv论文检索等
"""

from addition_tool.arxiv_tool import search_papers, get_paper_by_id, search_by_author

__all__ = ['search_papers', 'get_paper_by_id', 'search_by_author']