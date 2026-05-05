"""
轻量级论文相关性评分模块

本模块实现了不依赖 embedding API 的论文相关性评分器，适用于课程设计场景。

评分维度（5 个维度，加权求和）：
1. 标题关键词匹配度（权重 42%）：研究主题与论文标题的词汇重叠率
2. 摘要关键词匹配度（权重 28%）：研究主题与论文摘要的词汇重叠率
3. 引用数评分（权重 14%）：使用 log 平滑处理，避免高引用论文过度主导
4. 年份新鲜度（权重 10%）：越新越高分，12 年前的论文归零
5. 来源权重（权重 6%）：Semantic Scholar（有引用数据）> arXiv

设计考量：
- 不使用 torch/sentence-transformers，避免大依赖和 GPU 需求
- 不调用 embedding API（如 DeepSeek），避免 chat 模型无 embeddings endpoint 时的降级问题
- 纯 Python 实现，可解释性强，适合课程设计答辩
"""

import logging
import math
import re
from datetime import datetime
from typing import Dict, Set

logger = logging.getLogger(__name__)


class LightweightRelevanceScorer:
    """
    轻量级论文相关性评分器

    基于关键词匹配、引用数、年份、来源等多维度计算论文与研究主题的相关性。
    无需外部依赖（torch、embedding API），纯 Python 实现。
    """

    # 停用词集合：这些词在匹配时会被忽略（中英文常见停用词）
    STOPWORDS = {
        "a", "an", "and", "are", "as", "at", "based", "by", "for", "from",
        "in", "is", "of", "on", "or", "the", "to", "using", "with", "研究",
        "方法", "模型", "系统", "应用", "基于"
    }

    def score(self, paper: Dict, topic: str) -> float:
        """
        计算论文与研究主题的相关性评分

        Args:
            paper: 论文数据字典（需包含 title、abstract、citation_count、year、source）
            topic: 研究主题字符串

        Returns:
            相关性评分（0.0 ~ 1.0，越高越相关）
        """
        # 将主题和论文文本转为 token 集合（分词 + 去停用词）
        topic_tokens = self._tokens(topic)
        title_tokens = self._tokens(paper.get("title") or "")
        abstract_tokens = self._tokens(paper.get("abstract") or "")

        # 计算各维度评分
        title_score = self._overlap(topic_tokens, title_tokens)       # 标题匹配度
        abstract_score = self._overlap(topic_tokens, abstract_tokens)  # 摘要匹配度
        citation_score = self._citation_score(paper.get("citation_count") or 0)  # 引用数
        year_score = self._year_score(paper.get("year"))               # 年份新鲜度
        source_score = 1.0 if paper.get("source") == "semantic_scholar" else 0.75  # 来源权重

        # 加权求和（各权重之和为 1.0）
        score = (
            title_score * 0.42      # 标题最重要：直接反映论文主题
            + abstract_score * 0.28  # 摘要次之：包含更多上下文
            + citation_score * 0.14  # 引用数：学术影响力指标
            + year_score * 0.10      # 年份：新论文通常更前沿
            + source_score * 0.06    # 来源：Semantic Scholar 数据更丰富
        )
        # 限制在 [0, 1] 范围内，保留 4 位小数
        return round(min(max(score, 0.0), 1.0), 4)

    def _tokens(self, text: str) -> Set[str]:
        """
        文本分词：提取英文单词和中文字符，转小写，过滤停用词

        分词规则：
        - 英文：匹配连续的字母数字序列（如 "depth_completion" → "depth_completion"）
        - 中文：逐字匹配（如 "深度" → {"深", "度"}）
        - 过滤：单个英文字符和停用词被移除
        """
        raw_tokens = re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]", text.lower())
        return {
            token
            for token in raw_tokens
            if (len(token) > 1 or "\u4e00" <= token <= "\u9fff") and token not in self.STOPWORDS
        }

    def _overlap(self, topic_tokens: Set[str], candidate_tokens: Set[str]) -> float:
        """
        计算两个 token 集合的重叠率（Jaccard 相似度的变体）

        公式：匹配数 / 主题 token 数
        这样设计是因为论文文本通常比主题长，用主题 token 作为分母更合理。
        """
        if not topic_tokens or not candidate_tokens:
            return 0.0
        matched = len(topic_tokens & candidate_tokens)
        return matched / len(topic_tokens)

    def _citation_score(self, citation_count: int) -> float:
        """
        引用数评分：使用 log 平滑处理

        公式：log(1 + count) / log(1 + 5000)
        - 使用 log1p 避免 log(0) 问题
        - 以 5000 次引用作为归一化基准（顶级论文的引用量级）
        - 效果：0 引用 → 0 分，5000 引用 → 1 分，中间对数增长
        """
        try:
            count = max(int(citation_count), 0)
        except (TypeError, ValueError):
            count = 0
        return min(1.0, math.log1p(count) / math.log1p(5000))

    def _year_score(self, year: int) -> float:
        """
        年份新鲜度评分：线性衰减

        公式：max(0, 1 - age / 12)
        - 当前年份的论文 → 1.0 分
        - 12 年前的论文 → 0.0 分
        - 中间线性衰减
        """
        try:
            year = int(year)
        except (TypeError, ValueError):
            return 0.0
        current_year = datetime.utcnow().year
        age = max(current_year - year, 0)
        return max(0.0, 1.0 - age / 12)


def get_relevance_scorer() -> LightweightRelevanceScorer:
    """工厂函数：获取相关性评分器实例"""
    return LightweightRelevanceScorer()


def get_embedding_service() -> LightweightRelevanceScorer:
    """兼容旧接口（已废弃），打印警告后返回评分器"""
    logger.warning("get_embedding_service() is deprecated; using lightweight scorer instead.")
    return get_relevance_scorer()
