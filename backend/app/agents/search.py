import logging
from typing import List, Dict
from app.services.search import get_search_service, SearchAPIError

logger = logging.getLogger(__name__)


class SearchAgent:
    def __init__(self):
        self.search_service = get_search_service()

    async def run(
        self,
        search_queries: List[str],
        year_from: int,
        year_to: int,
        limit: int
    ) -> List[Dict]:
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
            logger.error(f"SearchAgent error: {e}")
            return []
