"""
文献检索 Agent（SearchAgent）

职责：调用 SearchService 从 arXiv 和 Semantic Scholar 检索相关论文。

工作流程：
1. 接收 QueryAgent 生成的搜索查询列表
2. 调用 SearchService.search_papers() 执行双源检索
3. 返回去重后的论文列表

注意：SearchAgent 本身不排序，排序由下游的 RankAgent 负责。
"""

import logging
from typing import List, Dict
from app.services.search import get_search_service, SearchAPIError

logger = logging.getLogger(__name__)


class SearchAgent:
    """文献检索 Agent：封装 SearchService，提供统一的论文检索接口"""

    def __init__(self, search_service=None):
        """
        Args:
            search_service: 搜索服务实例（可选，默认从工厂函数创建）
        """
        self.search_service = search_service or get_search_service()

    async def run(
        self,
        search_queries: List[str],
        year_from: int,
        year_to: int,
        limit: int
    ) -> List[Dict]:
        """
        执行文献检索

        Args:
            search_queries: 搜索查询语句列表（来自 QueryAgent）
            year_from: 检索起始年份
            year_to: 检索结束年份
            limit: 最大返回论文数

        Returns:
            去重后的论文列表，每个论文包含 title、authors、abstract 等字段
        """
        logger.info(f"SearchAgent: Searching with {len(search_queries)} queries, limit={limit}")

        try:
            papers = await self.search_service.search_papers(
                queries=search_queries,
                year_from=year_from,
                year_to=year_to,
                limit=limit
            )
            logger.info(f"SearchAgent: Found {len(papers)} papers")
            return papers
        except SearchAPIError as e:
            # 搜索 API 异常时返回空列表（不会中断整个工作流）
            logger.error(f"SearchAgent error: {e}")
            return []
