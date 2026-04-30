import logging
import math
import re
from datetime import datetime
from typing import Dict, Set

logger = logging.getLogger(__name__)


class LightweightRelevanceScorer:
    """Dependency-free paper scorer for course demos without torch or embedding APIs."""

    STOPWORDS = {
        "a", "an", "and", "are", "as", "at", "based", "by", "for", "from",
        "in", "is", "of", "on", "or", "the", "to", "using", "with", "研究",
        "方法", "模型", "系统", "应用", "基于"
    }

    def score(self, paper: Dict, topic: str) -> float:
        topic_tokens = self._tokens(topic)
        title_tokens = self._tokens(paper.get("title") or "")
        abstract_tokens = self._tokens(paper.get("abstract") or "")

        title_score = self._overlap(topic_tokens, title_tokens)
        abstract_score = self._overlap(topic_tokens, abstract_tokens)
        citation_score = self._citation_score(paper.get("citation_count") or 0)
        year_score = self._year_score(paper.get("year"))
        source_score = 1.0 if paper.get("source") == "semantic_scholar" else 0.75

        score = (
            title_score * 0.42
            + abstract_score * 0.28
            + citation_score * 0.14
            + year_score * 0.10
            + source_score * 0.06
        )
        return round(min(max(score, 0.0), 1.0), 4)

    def _tokens(self, text: str) -> Set[str]:
        raw_tokens = re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]", text.lower())
        return {
            token
            for token in raw_tokens
            if (len(token) > 1 or "\u4e00" <= token <= "\u9fff") and token not in self.STOPWORDS
        }

    def _overlap(self, topic_tokens: Set[str], candidate_tokens: Set[str]) -> float:
        if not topic_tokens or not candidate_tokens:
            return 0.0
        matched = len(topic_tokens & candidate_tokens)
        return matched / len(topic_tokens)

    def _citation_score(self, citation_count: int) -> float:
        try:
            count = max(int(citation_count), 0)
        except (TypeError, ValueError):
            count = 0
        return min(1.0, math.log1p(count) / math.log1p(5000))

    def _year_score(self, year: int) -> float:
        try:
            year = int(year)
        except (TypeError, ValueError):
            return 0.0
        current_year = datetime.utcnow().year
        age = max(current_year - year, 0)
        return max(0.0, 1.0 - age / 12)


def get_relevance_scorer() -> LightweightRelevanceScorer:
    return LightweightRelevanceScorer()


def get_embedding_service() -> LightweightRelevanceScorer:
    logger.warning("get_embedding_service() is deprecated; using lightweight scorer instead.")
    return get_relevance_scorer()
