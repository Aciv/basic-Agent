"""
arXiv论文检索工具
使用arXiv API搜索学术论文
"""

import arxiv
import datetime
from typing import Optional, Dict, Any, List
from tool.tools import tool


@tool
def search_papers(
    query: str,
    max_results: int = 10,
    sort_by: str = "relevance",
    sort_order: str = "descending",
    categories: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> Dict[str, Any]:
    """
    搜索arXiv学术论文,使用arXiv API搜索学术论文，支持关键词、分类、日期范围等过滤条件。
    
    :param query: 搜索查询关键词，例如："machine learning" 或 "transformer"
    :param max_results: 最大返回结果数量，默认10，最大100
    :param sort_by: 排序方式，可选："relevance"（相关性）、"lastUpdatedDate"（最后更新日期）、"submittedDate"（提交日期）
    :param sort_order: 排序顺序，可选："ascending"（升序）、"descending"（降序）
    :param categories: arXiv分类，例如："cs.CL,cs.AI" 或 "cs.*,math.*"。多个分类用逗号分隔
    :param date_from: 起始日期，格式："YYYY-MM-DD"，例如："2024-01-01"
    :param date_to: 结束日期，格式："YYYY-MM-DD"，例如："2024-12-31"
    
    :return: 包含搜索结果和论文详细信息的字典
    """
    try:
        # 验证参数
        if max_results <= 0 or max_results > 100:
            return {
                "success": False,
                "message": "max_results必须在1到100之间",
                "error": "Invalid max_results value"
            }
        
        # 构建查询字符串
        search_query = query
        
        # 添加分类过滤
        if categories:
            # 处理多个分类
            category_list = [cat.strip() for cat in categories.split(',')]
            category_queries = []
            for cat in category_list:
                if cat.endswith('.*'):
                    # 通配符分类
                    category_queries.append(f"cat:{cat}")
                else:
                    # 具体分类
                    category_queries.append(f"cat:{cat}")
            
            if category_queries:
                if len(category_queries) == 1:
                    search_query = f"({search_query}) AND {category_queries[0]}"
                else:
                    search_query = f"({search_query}) AND ({' OR '.join(category_queries)})"
        
        # 添加日期过滤（通过查询字符串实现）

        date_query_parts = []
        
        if date_from:
            try:
                # 1. 验证并解析输入的 YYYY-MM-DD 格式
                dt_from = datetime.datetime.strptime(date_from, "%Y-%m-%d")
            except ValueError:
                return {
                    "success": False,
                    "message": "date_from格式错误，应为YYYY-MM-DD格式",
                    "error": "Invalid date_from format"
                }
        else:
            dt_from = datetime.datetime.strptime("1991-01-01", "%Y-%m-%d")

        if date_to:
            try:
                # 1. 验证并解析输入的 YYYY-MM-DD 格式
                dt_to = datetime.datetime.strptime(date_to, "%Y-%m-%d")
            except ValueError:
                return {
                    "success": False,
                    "message": "date_to格式错误，应为YYYY-MM-DD格式",
                    "error": "Invalid date_to format"
                }
        else:
            dt_to = datetime.datetime.strptime(str(datetime.date.today()), "%Y-%m-%d")

        # 2. 转换为 arXiv 需要的 YYYYMMDD235959 (当天23点59分59秒)
        arxiv_date_from = dt_from.strftime("%Y%m%d000000")
        date_query_parts.append(f"submittedDate:[{arxiv_date_from}")

        arxiv_date_to = dt_to.strftime("%Y%m%d235959")
        

        date_query_parts[0] = date_query_parts[0] + f" TO {arxiv_date_to}]"

        

        search_query = f"({search_query}) AND {date_query_parts[0]}"
        
        # 设置排序
        sort_criterion_map = {
            "relevance": arxiv.SortCriterion.Relevance,
            "lastUpdatedDate": arxiv.SortCriterion.LastUpdatedDate,
            "submittedDate": arxiv.SortCriterion.SubmittedDate
        }
        
        sort_order_map = {
            "ascending": arxiv.SortOrder.Ascending,
            "descending": arxiv.SortOrder.Descending
        }
        
        sort_criterion = sort_criterion_map.get(sort_by, arxiv.SortCriterion.Relevance)
        sort_order_enum = sort_order_map.get(sort_order, arxiv.SortOrder.Descending)

        # 创建搜索对象
        search = arxiv.Search(
            query=search_query,
            max_results=max_results,
            sort_by=sort_criterion,
            sort_order=sort_order_enum
        )
        

        # 执行搜索
        client = arxiv.Client(page_size=100,num_retries=2)
        results = list(client.results(search))

        
        # 处理结果
        papers = []
        for paper in results:
            paper_info = {
                "title": paper.title,
                "authors": [str(author) for author in paper.authors],
                "published": paper.published.isoformat() if paper.published else None,
                "updated": paper.updated.isoformat() if paper.updated else None,
                "summary": paper.summary,
                "pdf_url": paper.pdf_url,
                "entry_id": paper.entry_id,
                "primary_category": paper.primary_category,
                "categories": paper.categories,
                "comment": paper.comment,
                "journal_ref": paper.journal_ref,
                "doi": paper.doi,
                "links": [{"href": link.href, "title": link.title, "rel": link.rel} for link in paper.links]
            }
            papers.append(paper_info)
        
        # 返回结果
        return {
            "success": True,
            "message": f"成功找到 {len(papers)} 篇论文",
            "query": query,
            "search_query": search_query,
            "total_results": len(papers),
            "papers": papers,
            "search_parameters": {
                "max_results": max_results,
                "sort_by": sort_by,
                "sort_order": sort_order,
                "categories": categories,
                "date_from": date_from,
                "date_to": date_to
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"搜索论文时发生错误: {str(e)}",
            "error": str(e),
            "query": query
        }


@tool
def get_paper_by_id(paper_id: str) -> Dict[str, Any]:
    """
    根据论文ID获取论文详细信息
    
    通过arXiv论文ID（如：2401.12345v1）获取论文的完整信息。
    
    :param paper_id: arXiv论文ID，例如："2401.12345v1" 或 "2401.12345"
    :return: 论文详细信息
    """
    try:
        # 确保ID格式正确
        if not paper_id:
            return {
                "success": False,
                "message": "论文ID不能为空",
                "error": "Empty paper_id"
            }
        
        # 创建客户端
        client = arxiv.Client(page_size=100,num_retries=2)
        
        # 搜索特定论文
        search = arxiv.Search(id_list=[paper_id])
        results = list(client.results(search))
        
        if not results:
            return {
                "success": False,
                "message": f"未找到ID为 {paper_id} 的论文",
                "paper_id": paper_id,
                "error": "Paper not found"
            }
        
        paper = results[0]
        
        # 构建论文信息
        paper_info = {
            "title": paper.title,
            "authors": [str(author) for author in paper.authors],
            "published": paper.published.isoformat() if paper.published else None,
            "updated": paper.updated.isoformat() if paper.updated else None,
            "summary": paper.summary,
            "pdf_url": paper.pdf_url,
            "entry_id": paper.entry_id,
            "primary_category": paper.primary_category,
            "categories": paper.categories,
            "comment": paper.comment,
            "journal_ref": paper.journal_ref,
            "doi": paper.doi,
            "links": [{"href": link.href, "title": link.title, "rel": link.rel} for link in paper.links]
        }
        
        return {
            "success": True,
            "message": f"成功获取论文: {paper.title}",
            "paper": paper_info,
            "paper_id": paper_id
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"获取论文时发生错误: {str(e)}",
            "error": str(e),
            "paper_id": paper_id
        }


@tool
def search_by_author(author_name: str, max_results: int = 10) -> Dict[str, Any]:
    """
    根据作者姓名搜索论文
    
    搜索特定作者在arXiv上发表的论文。
    
    :param author_name: 作者姓名，例如："Yann LeCun" 或 "Hinton"
    :param max_results: 最大返回结果数量，默认10，最大50
    :return: 作者相关的论文列表
    """
    try:
        # 验证参数
        if max_results <= 0 or max_results > 50:
            return {
                "success": False,
                "message": "max_results必须在1到50之间",
                "error": "Invalid max_results value"
            }
        
        # 构建作者搜索查询
        search_query = f'au:"{author_name}"'
        
        # 创建搜索对象
        search = arxiv.Search(
            query=search_query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending
        )
        
        # 执行搜索
        client = arxiv.Client(page_size=100,num_retries=2)
        results = list(client.results(search))
        
        # 处理结果
        papers = []
        for paper in results:
            paper_info = {
                "title": paper.title,
                "authors": [str(author) for author in paper.authors],
                "published": paper.published.isoformat() if paper.published else None,
                "updated": paper.updated.isoformat() if paper.updated else None,
                "summary": paper.summary[:500] + "..." if len(paper.summary) > 500 else paper.summary,
                "pdf_url": paper.pdf_url,
                "entry_id": paper.entry_id,
                "primary_category": paper.primary_category
            }
            papers.append(paper_info)
        
        return {
            "success": True,
            "message": f"找到 {len(papers)} 篇作者为 {author_name} 的论文",
            "author": author_name,
            "total_results": len(papers),
            "papers": papers
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"搜索作者论文时发生错误: {str(e)}",
            "error": str(e),
            "author_name": author_name
        }


# 导出所有工具
__all__ = ['search_papers', 'get_paper_by_id', 'search_by_author']