import logging
from typing import List, Dict
from app.services.embedding import get_relevance_scorer

logger = logging.getLogger(__name__)


class RankAgent:
    def __init__(self):
        self.scorer = get_relevance_scorer()

    async def run(
        self,
        papers: List[Dict],
        topic: str,
        limit: int = 10
    ) -> List[Dict]:
        logger.info(f"RankAgent: Ranking {len(papers)} papers")

        if not papers:
            return []

        scored_papers = []
        for paper in papers:
            scored_papers.append({
                **paper,
                "relevance_score": self.scorer.score(paper, topic)
            })

        scored_papers.sort(
            key=lambda x: (
                x["relevance_score"],
                x.get("citation_count") or 0,
                x.get("year") or 0,
            ),
            reverse=True,
        )

        top_papers = scored_papers[:limit]

        for i, paper in enumerate(top_papers, 1):
            paper["rank"] = i
            paper["paper_index"] = i

        logger.info(f"RankAgent: Selected top {len(top_papers)} papers")
        return top_papers
