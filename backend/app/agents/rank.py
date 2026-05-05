"""
文献排序 Agent（RankAgent）

职责：对检索到的论文进行多维度相关性排序。

排序策略（不依赖 embedding API，轻量可解释）：
1. 关键词匹配度（权重 42%）：研究主题与论文标题/摘要的词汇重叠度
2. 摘要相关度（权重 28%）：研究主题与论文摘要的匹配程度
3. 引用数（权重 14%）：论文被引用次数（log 平滑处理）
4. 年份新鲜度（权重 10%）：越新越高分，12 年前的论文归零
5. 来源权重（权重 6%）：Semantic Scholar > arXiv（前者有引用数数据）

最终返回 top-K 论文，并为每篇论文添加 paper_index 编号。
"""

import logging
from typing import List, Dict
from app.services.embedding import get_relevance_scorer

logger = logging.getLogger(__name__)


class RankAgent:
    """文献排序 Agent：基于多维度评分对论文进行排序和筛选"""

    def __init__(self, scorer=None):
        """
        Args:
            scorer: 相关性评分器实例（可选，默认从工厂函数创建）
        """
        self.scorer = scorer or get_relevance_scorer()

    async def run(
        self,
        papers: List[Dict],
        topic: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        执行文献排序

        Args:
            papers: 待排序的论文列表
            topic: 研究主题（用于计算相关性）
            limit: 返回的论文数量上限

        Returns:
            排序后的 top-K 论文列表，每篇包含 rank、paper_index、relevance_score 字段
        """
        logger.info(f"RankAgent: Ranking {len(papers)} papers")

        if not papers:
            return []

        # 为每篇论文计算相关性评分
        scored_papers = []
        for paper in papers:
            scored_papers.append({
                **paper,
                "relevance_score": self.scorer.score(paper, topic)
            })

        # 多维度排序：相关性评分 > 引用数 > 年份（均为降序）
        scored_papers.sort(
            key=lambda x: (
                x["relevance_score"],           # 主排序键：相关性评分
                x.get("citation_count") or 0,   # 次排序键：引用数
                x.get("year") or 0,             # 第三排序键：年份（越新越好）
            ),
            reverse=True,  # 降序排列
        )

        # 取 top-K
        top_papers = scored_papers[:limit]

        # 为每篇论文添加排序编号（从 1 开始），后续用于引用标识 [paper_1]
        for i, paper in enumerate(top_papers, 1):
            paper["rank"] = i
            paper["paper_index"] = i

        logger.info(f"RankAgent: Selected top {len(top_papers)} papers")
        return top_papers
