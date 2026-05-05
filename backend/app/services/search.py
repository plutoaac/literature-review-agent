"""
学术文献搜索服务模块

提供双源学术论文检索能力：
1. Semantic Scholar：通过 REST API 检索，有引用数、作者等丰富元数据
2. arXiv：通过 arxiv Python 库检索，覆盖计算机科学/物理/数学等领域

搜索策略：
- 优先从 arXiv 检索（免费、无限流）
- 如果结果不足，再从 Semantic Scholar 补充
- 两个源的结果按标题去重
- 中文查询自动过滤（arXiv 不支持中文检索）
"""

import asyncio
import httpx
import arxiv
import logging
from typing import List, Dict, Set
import re

from app.services.query_expander import expand_academic_queries

logger = logging.getLogger(__name__)


class SearchAPIError(Exception):
    """搜索 API 异常基类"""
    pass


class SemanticScholarSearch:
    """
    Semantic Scholar 搜索客户端

    使用 Semantic Scholar Academic Graph API v1 检索论文。
    API 文档：https://api.semanticscholar.org/api-docs/
    """
    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    async def search(
        self,
        queries: List[str],
        year_from: int,
        year_to: int,
        limit: int
    ) -> List[Dict]:
        """
        批量搜索论文

        Args:
            queries: 搜索查询列表
            year_from: 起始年份
            year_to: 结束年份
            limit: 最大返回数

        Returns:
            去重后的论文列表
        """
        all_papers = []
        seen_ids: Set[str] = set()  # 按 paperId 去重

        async with httpx.AsyncClient(timeout=30.0) as client:
            for query in queries:
                try:
                    papers = await self._search_single(client, query, year_from, year_to, limit)
                    for paper in papers:
                        paper_id = paper.get("externalId") or paper.get("paperId")
                        if paper_id and paper_id not in seen_ids:
                            seen_ids.add(paper_id)
                            all_papers.append(self._parse_paper(paper, "semantic_scholar"))
                except Exception as e:
                    logger.warning("Semantic Scholar search failed for query '%s': %s", query, e)
                    continue

        return all_papers

    async def _search_single(
        self,
        client: httpx.AsyncClient,
        query: str,
        year_from: int,
        year_to: int,
        limit: int
    ) -> List[Dict]:
        """
        单次搜索请求

        使用 /paper/search 端点，支持关键词搜索 + 年份过滤。
        fields 参数指定返回的字段列表。
        """
        url = f"{self.BASE_URL}/paper/search"

        params = {
            "query": query,
            "year": f"{year_from}-{year_to}",        # 年份范围过滤
            "limit": min(limit, 100),                 # API 单次最多 100 条
            "fields": "paperId,title,authors,year,abstract,venue,citationCount,url,externalId"
        }

        headers = {"Accept": "application/json"}

        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

        return data.get("data", [])  # API 返回格式：{"data": [...], "total": N, "offset": N}

    def _parse_paper(self, paper: Dict, source: str) -> Dict:
        """
        将 Semantic Scholar 返回的论文数据转为统一格式

        统一格式包含：external_id、title、authors、year、abstract、venue、citation_count、url、source
        """
        authors = []
        if paper.get("authors"):
            # 最多取前 10 位作者
            authors = [author.get("name", "Unknown") for author in paper["authors"][:10]]

        return {
            "external_id": paper.get("externalId") or paper.get("paperId"),
            "title": paper.get("title", "Untitled"),
            "authors": authors,
            "year": paper.get("year"),
            "abstract": paper.get("abstract"),
            "venue": paper.get("venue"),
            "citation_count": paper.get("citationCount", 0),
            "url": paper.get("url"),
            "source": source
        }


class ArxivSearch:
    """
    arXiv 搜索客户端

    使用 arxiv Python 库检索论文。
    arXiv 是开放获取的预印本服务器，覆盖计算机科学、物理、数学等领域。
    """

    def search(
        self,
        queries: List[str],
        year_from: int,
        year_to: int,
        limit: int
    ) -> List[Dict]:
        """
        批量搜索论文

        Args:
            queries: 搜索查询列表
            year_from: 起始年份
            year_to: 结束年份
            limit: 最大返回数

        Returns:
            去重后的论文列表
        """
        all_papers = []
        seen_ids: Set[str] = set()  # 按 entry_id 去重

        for query in queries:
            # arXiv 不支持中文查询，跳过包含中文的查询
            if self._contains_chinese(query):
                continue

            # 构建 arXiv 查询语法（如 "all:depth AND all:completion"）
            arxiv_query = self._build_query(query)
            if not arxiv_query:
                continue

            client = arxiv.Search(
                query=arxiv_query,
                max_results=max(limit, 10),
                sort_by=arxiv.SortCriterion.Relevance
            )

            try:
                for result in client.results():
                    # 年份过滤
                    if result.published and not (year_from <= result.published.year <= year_to):
                        continue
                    # 去重
                    if result.entry_id in seen_ids:
                        continue
                    seen_ids.add(result.entry_id)

                    authors = [author.name for author in result.authors[:10]]

                    all_papers.append({
                        "external_id": result.entry_id,
                        "title": result.title,
                        "authors": authors,
                        "year": result.published.year if result.published else None,
                        "abstract": result.summary,
                        "venue": "arXiv",
                        "citation_count": 0,  # arXiv API 不提供引用数
                        "url": result.entry_id,
                        "source": "arxiv"
                    })

                    if len(all_papers) >= limit:
                        return all_papers
            except Exception as e:
                logger.warning("arXiv search failed for query '%s': %s", query, e)
                continue

        return all_papers

    def _build_query(self, query: str) -> str:
        """
        构建 arXiv 搜索查询语法

        规则：
        - 提取英文单词和数字作为 token
        - 过滤停用词（for、with、and 等）
        - 用 AND 连接前 5 个 token（如 "all:depth AND all:completion"）
        """
        tokens = [
            token.lower()
            for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", query or "")
            if len(token) > 1
        ]
        # 常见停用词（在 arXiv 查询中无意义）
        stopwords = {"for", "with", "and", "the", "of", "in", "on", "a", "an", "to"}
        tokens = [token for token in tokens if token not in stopwords]

        if not tokens:
            return ""

        # 短查询（≤2 个 token）：全部用 AND 连接
        if len(tokens) <= 2:
            return " AND ".join([f"all:{token}" for token in tokens])

        # 长查询：取前 5 个 token
        must_have = tokens[:5]
        return " AND ".join([f"all:{token}" for token in must_have])

    def _contains_chinese(self, text: str) -> bool:
        """检测文本是否包含中文字符"""
        return bool(re.search(r"[\u4e00-\u9fff]", text or ""))


class SearchService:
    """
    统一搜索服务：整合 arXiv 和 Semantic Scholar 两个数据源

    搜索策略：
    1. 先扩展查询（中文学术术语 → 英文）
    2. 优先从 arXiv 检索（免费、快速）
    3. 如果结果不足，再从 Semantic Scholar 补充
    4. 两个源的结果按标题去重
    """

    def __init__(self):
        self.semantic_scholar = SemanticScholarSearch()
        self.arxiv = ArxivSearch()

    async def search_papers(
        self,
        queries: List[str],
        year_from: int,
        year_to: int,
        limit: int
    ) -> List[Dict]:
        """
        执行双源论文检索

        Args:
            queries: 原始搜索查询列表
            year_from: 起始年份
            year_to: 结束年份
            limit: 目标返回数量

        Returns:
            去重后的论文列表（可能超过 limit，最多 2*limit）
        """
        all_papers = []
        seen_titles: Set[str] = set()  # 按标题去重（两个源的 ID 格式不同）

        # 扩展查询：中文学术术语转英文，增加检索覆盖率
        expanded_queries = expand_academic_queries(queries)
        logger.info("Expanded search queries: %s", expanded_queries)

        # 第一步：从 arXiv 检索（同步库，通过 to_thread 包装为异步）
        try:
            arxiv_papers = await asyncio.to_thread(
                self.arxiv.search,
                expanded_queries,
                year_from,
                year_to,
                limit,
            )
            for paper in arxiv_papers:
                title_lower = paper["title"].strip().lower()
                if title_lower and title_lower not in seen_titles:
                    seen_titles.add(title_lower)
                    all_papers.append(paper)
        except Exception as e:
            logger.warning("arXiv search failed, will rely on Semantic Scholar: %s", e)

        # 第二步：如果结果不足，从 Semantic Scholar 补充
        if len(all_papers) < limit:
            try:
                ss_papers = await self.semantic_scholar.search(
                    expanded_queries,
                    year_from,
                    year_to,
                    max(limit, limit - len(all_papers))  # 请求剩余数量
                )
                for paper in ss_papers:
                    title_lower = paper["title"].strip().lower()
                    if title_lower and title_lower not in seen_titles:
                        seen_titles.add(title_lower)
                        all_papers.append(paper)
            except Exception as e:
                logger.warning("Semantic Scholar search failed: %s", e)

        # 最多返回 2*limit 条（给 RankAgent 更多候选）
        return all_papers[: max(limit * 2, limit)]


def get_search_service() -> SearchService:
    """工厂函数：获取搜索服务实例"""
    return SearchService()
