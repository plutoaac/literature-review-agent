import asyncio
import httpx
import arxiv
import logging
from typing import List, Dict, Set

logger = logging.getLogger(__name__)


class SearchAPIError(Exception):
    pass


class SemanticScholarSearch:
    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    async def search(
        self,
        queries: List[str],
        year_from: int,
        year_to: int,
        limit: int
    ) -> List[Dict]:
        all_papers = []
        seen_ids: Set[str] = set()

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
        url = f"{self.BASE_URL}/paper/search"

        params = {
            "query": query,
            "year": f"{year_from}-{year_to}",
            "limit": min(limit, 100),
            "fields": "paperId,title,authors,year,abstract,venue,citationCount,url,externalId"
        }

        headers = {"Accept": "application/json"}

        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

        return data.get("data", [])

    def _parse_paper(self, paper: Dict, source: str) -> Dict:
        authors = []
        if paper.get("authors"):
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
    def search(
        self,
        queries: List[str],
        year_from: int,
        year_to: int,
        limit: int
    ) -> List[Dict]:
        all_papers = []
        seen_ids: Set[str] = set()

        client = arxiv.Search(
            query=" OR ".join([f'"{q}"' for q in queries]),
            max_results=limit,
            sort_by=arxiv.SortCriterion.Relevance
        )

        for result in client.results():
            if result.published and not (year_from <= result.published.year <= year_to):
                continue
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
                "citation_count": 0,
                "url": result.entry_id,
                "source": "arxiv"
            })

        return all_papers


class SearchService:
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
        all_papers = []
        seen_titles: Set[str] = set()

        try:
            ss_papers = await self.semantic_scholar.search(queries, year_from, year_to, limit)
            for paper in ss_papers:
                title_lower = paper["title"].strip().lower()
                if title_lower and title_lower not in seen_titles:
                    seen_titles.add(title_lower)
                    all_papers.append(paper)
        except Exception as e:
            logger.warning("Semantic Scholar failed, will rely on arXiv: %s", e)

        try:
            arxiv_papers = await asyncio.to_thread(
                self.arxiv.search,
                queries,
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
            logger.warning("arXiv search failed: %s", e)

        return all_papers[: max(limit * 2, limit)]


def get_search_service() -> SearchService:
    return SearchService()
